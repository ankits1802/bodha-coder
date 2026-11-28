from __future__ import annotations

import base64
from dataclasses import dataclass, replace
from datetime import timedelta
from typing import NoReturn

import qrcode
import qrcode.image.svg
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.deps import PRACTICE_CLAIM, ROLE_CLAIM, Client, PracticeAccess, needs_two_step, practice_access
from app.core.errors import Invalid, Unauthorized
from app.core.security import (
    PASSWORD_MIN_LENGTH,
    TokenError,
    digest,
    hash_password,
    issue_token,
    mfa_uri,
    random_token,
    read_token,
    verify_password,
)
from app.models import PRACTICE_REALM, Session, User, UserToken, utcnow
from app.services.account_lookup import account_by_email, normal_email
from app.services.audit_log import AGENT_LENGTH
from app.services.auth_events import SIGN_IN_FAILED, SIGNED_IN, AuthEventFacts, record_auth_event
from app.services.memberships import accept_invitations, landing_access
from app.services.rate_limits import LOGIN_PER_EMAIL, LOGIN_PER_IP, MFA_PER_USER, hit
from app.services.recovery_codes import replace_recovery_codes, use_recovery_code
from app.services.sso_policy import SsoRequired, SsoRoute, ensure_password_allowed
from app.services.two_step import accept_code, enrol_secret
from app.services.user_sessions import end_all_sessions

MFA_TOKEN_MINUTES = 5
TOKEN_HOURS = {"invite": 72, "reset": 1}
PASSWORD_EVENTS = {"invite": "password_set", "reset": "password_changed"}
SIGN_IN_REFUSED = "email or password is not correct"
SIGN_IN_AGAIN = "sign in again"
PASSWORD_METHOD = "password"
TWO_STEP_CODE = "two-step code"
RECOVERY_CODE = "recovery code"
PASSWORD_CHANGED = "password changed"
BREAK_GLASS_METHOD = "a break-glass password"
SSO_REQUIRED_DETAIL = "password: single sign-on required"


@dataclass(frozen=True)
class Tokens:
    access: str
    refresh: str
    user: User
    standing: PracticeAccess
    recovery_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class MfaChallenge:
    step: str
    token: str


@dataclass(frozen=True)
class MfaEnrolment:
    secret: str
    uri: str
    qr_image: str


@dataclass(frozen=True)
class PendingSignIn:
    user: User
    method: str
    standing: PracticeAccess


async def login(
    db: AsyncSession, email: str, password: str, *, realms: tuple[str, ...], client: Client
) -> Tokens | MfaChallenge:
    address = normal_email(email)
    await hit(db, LOGIN_PER_EMAIL, address)
    await hit(db, LOGIN_PER_IP, client.ip)
    user = await account_by_email(db, address, realms)
    route = await _password_route(db, address, user, realms=realms, client=client)
    password_ok = verify_password(password, user.password_hash if user else None)
    if user is None or user.status != "active" or not password_ok:
        realm = realms[0] if len(realms) == 1 else None
        facts = AuthEventFacts(client, detail=PASSWORD_METHOD, email=address, realm=realm)
        await _refuse(db, user, facts, SIGN_IN_REFUSED)
    return await _password_sign_in(db, user, route, client)


async def _password_route(
    db: AsyncSession, address: str, user: User | None, *, realms: tuple[str, ...], client: Client
) -> SsoRoute | None:
    if PRACTICE_REALM not in realms:
        return None
    try:
        return await ensure_password_allowed(db, address, user)
    except SsoRequired:
        facts = AuthEventFacts(client, detail=SSO_REQUIRED_DETAIL, email=address, realm=PRACTICE_REALM)
        await record_auth_event(db, SIGN_IN_FAILED, user, facts)
        await db.commit()
        raise


async def _password_sign_in(
    db: AsyncSession, user: User, route: SsoRoute | None, client: Client
) -> Tokens | MfaChallenge:
    if route is not None and route.required:
        return two_step_challenge(user, BREAK_GLASS_METHOD, await _standing(db, user, None))
    return await sign_in_user(db, user, method=PASSWORD_METHOD, client=client)


async def _refuse(db: AsyncSession, user: User | None, facts: AuthEventFacts, message: str) -> NoReturn:
    await record_auth_event(db, SIGN_IN_FAILED, user, facts)
    await db.commit()
    raise Unauthorized(message)


async def sign_in_user(
    db: AsyncSession, user: User, *, method: str, client: Client, practice_id: str | None = None
) -> Tokens | MfaChallenge:
    standing = await _standing(db, user, practice_id)
    if user.mfa_enabled or needs_two_step(standing):
        return two_step_challenge(user, method, standing)
    return await start_session(db, user, standing, method=method, client=client)


def two_step_challenge(user: User, method: str, standing: PracticeAccess) -> MfaChallenge:
    step = "verify" if user.mfa_enabled else "setup"
    claims = {"via": method, PRACTICE_CLAIM: standing.practice_id}
    return MfaChallenge(step, issue_token("mfa", user.id, MFA_TOKEN_MINUTES, **claims))


async def _standing(db: AsyncSession, user: User, practice_id: str | None) -> PracticeAccess:
    return await practice_access(db, user, practice_id) if practice_id else await landing_access(db, user)


async def _pending(db: AsyncSession, mfa_token: str, realms: tuple[str, ...]) -> PendingSignIn:
    try:
        claims = read_token(mfa_token, "mfa")
    except TokenError as error:
        raise Unauthorized(SIGN_IN_AGAIN) from error
    user = await db.get(User, claims["sub"])
    if user is None or user.status != "active" or user.realm not in realms:
        raise Unauthorized(SIGN_IN_AGAIN)
    standing = await _standing(db, user, claims.get(PRACTICE_CLAIM))
    return PendingSignIn(user, str(claims.get("via", PASSWORD_METHOD)), standing)


async def mfa_enrol(db: AsyncSession, mfa_token: str, realms: tuple[str, ...]) -> MfaEnrolment:
    user = (await _pending(db, mfa_token, realms)).user
    if user.mfa_enabled:
        raise Invalid("two-step verification is already set up")
    secret = enrol_secret(user)
    await db.commit()
    uri = mfa_uri(secret, user.email)
    svg = qrcode.make(uri, image_factory=qrcode.image.svg.SvgPathImage).to_string()
    return MfaEnrolment(secret, uri, "data:image/svg+xml;base64," + base64.b64encode(svg).decode())


async def mfa_verify(db: AsyncSession, mfa_token: str, code: str, *, realms: tuple[str, ...], client: Client) -> Tokens:
    pending = await _pending(db, mfa_token, realms)
    user = pending.user
    await hit(db, MFA_PER_USER, user.id)
    if not accept_code(user, code):
        await _refuse(db, user, AuthEventFacts(client, detail=TWO_STEP_CODE), "that code is not correct")
    if user.mfa_enabled:
        return await start_session(db, user, pending.standing, method=pending.method, client=client)
    user.mfa_enabled = True
    await record_auth_event(db, "two_step_on", user, AuthEventFacts(client))
    codes = await replace_recovery_codes(db, user)
    tokens = await start_session(db, user, pending.standing, method=pending.method, client=client)
    return replace(tokens, recovery_codes=codes)


async def mfa_recover(
    db: AsyncSession, mfa_token: str, recovery_code: str, *, realms: tuple[str, ...], client: Client
) -> Tokens:
    pending = await _pending(db, mfa_token, realms)
    user = pending.user
    await hit(db, MFA_PER_USER, user.id)
    if not user.mfa_enabled or not await use_recovery_code(db, user, recovery_code):
        await _refuse(db, user, AuthEventFacts(client, detail=RECOVERY_CODE), "that recovery code is not correct")
    await record_auth_event(db, "recovery_code_used", user, AuthEventFacts(client))
    method = f"{pending.method} and a recovery code"
    return await start_session(db, user, pending.standing, method=method, client=client)


async def start_session(
    db: AsyncSession, user: User, standing: PracticeAccess, *, method: str, client: Client, idp_two_step: bool = False
) -> Tokens:
    refresh = random_token()
    settings = get_settings()
    db.add(
        Session(
            user_id=user.id,
            practice_id=standing.practice_id,
            refresh_hash=digest(refresh),
            expires_at=utcnow() + timedelta(days=settings.refresh_token_days),
            ip=client.ip,
            user_agent=(client.agent or "")[:AGENT_LENGTH] or None,
            idp_two_step=idp_two_step,
        )
    )
    user.last_active_at = utcnow()
    if standing.practice_id is not None:
        user.last_practice_id = standing.practice_id
    facts = AuthEventFacts(client, practice_id=standing.practice_id, detail=f"with {method}")
    await record_auth_event(db, SIGNED_IN, user, facts)
    await db.commit()
    return Tokens(access_token_for(user, standing), refresh, user, standing)


def access_token_for(user: User, standing: PracticeAccess) -> str:
    minutes = get_settings().access_token_minutes
    claims = {"ver": user.token_version, PRACTICE_CLAIM: standing.practice_id, ROLE_CLAIM: standing.role}
    return issue_token("access", user.id, minutes, **claims)


async def refresh_session(db: AsyncSession, refresh: str, realms: tuple[str, ...]) -> Tokens:
    session = await db.scalar(select(Session).where(Session.refresh_hash == digest(refresh)))
    now = utcnow()
    if session is None or session.revoked_at is not None or session.expires_at < now:
        raise Unauthorized(SIGN_IN_AGAIN)
    if now - session.last_used_at > timedelta(minutes=get_settings().session_idle_minutes):
        session.revoked_at = now
        await db.commit()
        raise Unauthorized("signed out after inactivity")
    user = await db.get_one(User, session.user_id)
    if user.status != "active" or user.realm not in realms:
        raise Unauthorized(SIGN_IN_AGAIN)
    standing = await _standing(db, user, session.practice_id)
    if needs_two_step(standing) and not (user.mfa_enabled or session.idp_two_step):
        raise Unauthorized(SIGN_IN_AGAIN)
    rotated = random_token()
    session.refresh_hash, session.last_used_at, session.practice_id = digest(rotated), now, standing.practice_id
    await db.commit()
    return Tokens(access_token_for(user, standing), rotated, user, standing)


async def logout(db: AsyncSession, refresh: str | None, *, client: Client) -> None:
    if not refresh:
        return
    session = await db.scalar(select(Session).where(Session.refresh_hash == digest(refresh)))
    if session is None or session.revoked_at is not None:
        return
    session.revoked_at = utcnow()
    user = await db.get_one(User, session.user_id)
    await record_auth_event(db, "signed_out", user, AuthEventFacts(client, practice_id=session.practice_id))
    await db.commit()


async def issue_user_token(db: AsyncSession, user: User, purpose: str) -> str:
    token = random_token()
    db.add(
        UserToken(
            user_id=user.id,
            purpose=purpose,
            token_hash=digest(token),
            expires_at=utcnow() + timedelta(hours=TOKEN_HOURS[purpose]),
        )
    )
    return token


async def set_password(
    db: AsyncSession, token: str, password: str, realms: tuple[str, ...], client: Client
) -> Tokens | MfaChallenge:
    user = await _store_password(db, token, password, realms, client)
    route = await ensure_password_allowed(db, user.email, user) if user.realm == PRACTICE_REALM else None
    return await _password_sign_in(db, user, route, client)


async def _store_password(db: AsyncSession, token: str, password: str, realms: tuple[str, ...], client: Client) -> User:
    if len(password) < PASSWORD_MIN_LENGTH:
        raise Invalid(f"use at least {PASSWORD_MIN_LENGTH} characters")
    row = await db.scalar(select(UserToken).where(UserToken.token_hash == digest(token)))
    if row is None or row.used_at is not None or row.expires_at < utcnow():
        raise Unauthorized("this link has expired")
    user = await db.get_one(User, row.user_id)
    if user.realm not in realms:
        raise Unauthorized("this link has expired")
    if user.status == "blocked":
        raise Unauthorized("this account is blocked")
    if user.realm == PRACTICE_REALM:
        await ensure_password_allowed(db, user.email, user)
    await accept_invitations(db, user, client)
    user.password_hash, user.status, row.used_at = hash_password(password), "active", utcnow()
    await record_auth_event(db, PASSWORD_EVENTS[row.purpose], user, AuthEventFacts(client))
    await end_all_sessions(db, user, reason=PASSWORD_CHANGED, client=client)
    await db.commit()
    return user
