from __future__ import annotations

import base64
from dataclasses import dataclass, replace
from datetime import timedelta

import qrcode
import qrcode.image.svg
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.deps import ensure_practice_open
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
from app.models import Practice, Session, User, UserToken, utcnow
from app.services.audit_log import record_sign_in
from app.services.rate_limits import LOGIN_PER_EMAIL, LOGIN_PER_IP, MFA_PER_USER, hit
from app.services.recovery_codes import replace_recovery_codes, use_recovery_code
from app.services.two_step import accept_code, enrol_secret

MFA_TOKEN_MINUTES = 5
TOKEN_HOURS = {"invite": 72, "reset": 1}
SIGN_IN_FAILED = "email or password is not correct"
PASSWORD_METHOD = "password"


@dataclass(frozen=True)
class Tokens:
    access: str
    refresh: str
    user: User
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


async def login(
    db: AsyncSession, email: str, password: str, *, ip: str | None, agent: str | None
) -> Tokens | MfaChallenge:
    address = email.strip().lower()
    await hit(db, LOGIN_PER_EMAIL, address)
    await hit(db, LOGIN_PER_IP, ip)
    user = await db.scalar(select(User).where(User.email == address))
    password_ok = verify_password(password, user.password_hash if user else None)
    if user is None or user.status != "active" or not password_ok:
        raise Unauthorized(SIGN_IN_FAILED)
    return await sign_in_user(db, user, method=PASSWORD_METHOD, ip=ip, agent=agent)


async def sign_in_user(
    db: AsyncSession, user: User, *, method: str, ip: str | None, agent: str | None
) -> Tokens | MfaChallenge:
    practice = await _practice_for(db, user)
    if user.mfa_enabled or user.role == "hq" or (practice is not None and user.role in practice.mfa_roles):
        step = "verify" if user.mfa_enabled else "setup"
        return MfaChallenge(step, issue_token("mfa", user.id, MFA_TOKEN_MINUTES, via=method))
    return await start_session(db, user, method=method, ip=ip, agent=agent)


async def _practice_for(db: AsyncSession, user: User) -> Practice | None:
    if user.practice_id is None:
        return None
    practice = await db.get_one(Practice, user.practice_id)
    ensure_practice_open(practice)
    return practice


async def _pending(db: AsyncSession, mfa_token: str) -> PendingSignIn:
    try:
        claims = read_token(mfa_token, "mfa")
    except TokenError as error:
        raise Unauthorized("sign in again") from error
    user = await db.get(User, claims["sub"])
    if user is None or user.status != "active":
        raise Unauthorized("sign in again")
    await _practice_for(db, user)
    return PendingSignIn(user, str(claims.get("via", PASSWORD_METHOD)))


async def mfa_enrol(db: AsyncSession, mfa_token: str) -> MfaEnrolment:
    user = (await _pending(db, mfa_token)).user
    if user.mfa_enabled:
        raise Invalid("two-step verification is already set up")
    secret = enrol_secret(user)
    await db.commit()
    uri = mfa_uri(secret, user.email)
    svg = qrcode.make(uri, image_factory=qrcode.image.svg.SvgPathImage).to_string()
    return MfaEnrolment(secret, uri, "data:image/svg+xml;base64," + base64.b64encode(svg).decode())


async def mfa_verify(db: AsyncSession, mfa_token: str, code: str, *, ip: str | None, agent: str | None) -> Tokens:
    pending = await _pending(db, mfa_token)
    user = pending.user
    await hit(db, MFA_PER_USER, user.id)
    if not accept_code(user, code):
        raise Unauthorized("that code is not correct")
    if user.mfa_enabled:
        return await start_session(db, user, method=pending.method, ip=ip, agent=agent)
    user.mfa_enabled = True
    codes = await replace_recovery_codes(db, user)
    tokens = await start_session(db, user, method=pending.method, ip=ip, agent=agent)
    return replace(tokens, recovery_codes=codes)


async def mfa_recover(
    db: AsyncSession, mfa_token: str, recovery_code: str, *, ip: str | None, agent: str | None
) -> Tokens:
    pending = await _pending(db, mfa_token)
    user = pending.user
    await hit(db, MFA_PER_USER, user.id)
    if not user.mfa_enabled or not await use_recovery_code(db, user, recovery_code):
        raise Unauthorized("that recovery code is not correct")
    return await start_session(db, user, method=f"{pending.method} and a recovery code", ip=ip, agent=agent)


async def start_session(db: AsyncSession, user: User, *, method: str, ip: str | None, agent: str | None) -> Tokens:
    refresh = random_token()
    settings = get_settings()
    db.add(
        Session(
            user_id=user.id,
            refresh_hash=digest(refresh),
            expires_at=utcnow() + timedelta(days=settings.refresh_token_days),
            ip=ip,
            user_agent=(agent or "")[:300] or None,
        )
    )
    record_sign_in(db, user, method=method, ip=ip, agent=agent)
    user.last_active_at = utcnow()
    await db.commit()
    return Tokens(_access_token(user), refresh, user)


def _access_token(user: User) -> str:
    return issue_token("access", user.id, get_settings().access_token_minutes, ver=user.token_version)


async def refresh_session(db: AsyncSession, refresh: str) -> Tokens:
    session = await db.scalar(select(Session).where(Session.refresh_hash == digest(refresh)))
    now = utcnow()
    if session is None or session.revoked_at is not None or session.expires_at < now:
        raise Unauthorized("sign in again")
    if now - session.last_used_at > timedelta(minutes=get_settings().session_idle_minutes):
        session.revoked_at = now
        await db.commit()
        raise Unauthorized("signed out after inactivity")
    user = await db.get_one(User, session.user_id)
    if user.status != "active":
        raise Unauthorized("sign in again")
    await _practice_for(db, user)
    rotated = random_token()
    session.refresh_hash, session.last_used_at = digest(rotated), now
    await db.commit()
    return Tokens(_access_token(user), rotated, user)


async def logout(db: AsyncSession, refresh: str | None) -> None:
    if refresh:
        await db.execute(update(Session).where(Session.refresh_hash == digest(refresh)).values(revoked_at=utcnow()))
        await db.commit()


async def end_all_sessions(db: AsyncSession, user: User) -> None:
    user.token_version += 1
    await db.execute(
        update(Session).where(Session.user_id == user.id, Session.revoked_at.is_(None)).values(revoked_at=utcnow())
    )


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


async def set_password(db: AsyncSession, token: str, password: str) -> None:
    if len(password) < PASSWORD_MIN_LENGTH:
        raise Invalid(f"use at least {PASSWORD_MIN_LENGTH} characters")
    row = await db.scalar(select(UserToken).where(UserToken.token_hash == digest(token)))
    if row is None or row.used_at is not None or row.expires_at < utcnow():
        raise Unauthorized("this link has expired")
    user = await db.get_one(User, row.user_id)
    if user.status == "blocked":
        raise Unauthorized("this account is blocked")
    user.password_hash, user.status, row.used_at = hash_password(password), "active", utcnow()
    await end_all_sessions(db, user)
    await db.commit()
