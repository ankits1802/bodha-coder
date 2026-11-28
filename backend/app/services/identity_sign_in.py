from __future__ import annotations

import hmac
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.oidc import IdentityProvider, ProviderIdentity, callback_url
from app.adapters.oidc_providers import IdentityRefused, ProviderUnreachable, UnverifiedEmail
from app.core.config import get_settings
from app.core.deps import Client
from app.core.errors import NotFound, Unauthorized
from app.core.realms import Site
from app.core.security import TokenError, issue_token, random_token, read_token
from app.models import PRACTICE_REALM, User, UserIdentity
from app.services.account_lookup import account_by_email
from app.services.auth import MfaChallenge, Tokens, sign_in_user
from app.services.auth_events import SIGN_IN_FAILED, AuthEventFacts, record_auth_event
from app.services.memberships import accept_invitations
from app.services.rate_limits import IDENTITY_PER_IP, hit
from app.services.sso_policy import SsoRequired, ensure_service_allowed

START_MINUTES = 10
START_TOKEN = "oidc_start"
SIGN_IN_INTENT = "sign_in"
SIGNUP_INTENT = "signup"
INTENTS = (SIGN_IN_INTENT, SIGNUP_INTENT)


class SignInRefused(Unauthorized):
    def __init__(self, reason: str) -> None:
        super().__init__(f"sign-in refused ({reason})")
        self.reason = reason


@dataclass(frozen=True)
class ProviderStart:
    url: str
    cookie: str


@dataclass(frozen=True)
class ProviderReturn:
    code: str | None
    state: str | None
    cookie: str | None


async def start(provider: IdentityProvider, site: Site, *, intent: str = SIGN_IN_INTENT) -> ProviderStart:
    if not provider.enabled:
        raise NotFound(f"{provider.label} sign-in is not set up")
    state, nonce, verifier = random_token(), random_token(), random_token()
    claims = {"nonce": nonce, "pkce": verifier, "idp": provider.name, "site": site.url, "intent": intent}
    cookie = issue_token(START_TOKEN, state, START_MINUTES, **claims)
    redirect_uri = callback_url(site.url, provider.name)
    url = await provider.authorization_url(state=state, nonce=nonce, verifier=verifier, redirect_uri=redirect_uri)
    return ProviderStart(url, cookie)


async def finish(
    db: AsyncSession,
    provider: IdentityProvider,
    returned: ProviderReturn,
    site: Site,
    *,
    client: Client,
) -> Tokens | MfaChallenge | ProviderIdentity:
    await hit(db, IDENTITY_PER_IP, client.ip)
    started = _started(returned, provider.name, site)
    identity = await _identity(provider, returned.code or "", started)
    try:
        return await _finish_for(
            db, identity, site, provider.label, client, signup=started.get("intent") == SIGNUP_INTENT
        )
    except SignInRefused as error:
        await _note_refusal(db, identity, site, f"{provider.label}: {error.reason}", client)
        raise


async def _finish_for(
    db: AsyncSession, identity: ProviderIdentity, site: Site, label: str, client: Client, *, signup: bool
) -> Tokens | MfaChallenge | ProviderIdentity:
    await _refuse_sso_domain(db, identity, site.realms)
    signups_open = get_settings().self_signup_enabled and site.takes_signups
    if signups_open and signup:
        await _refuse_foreign_subject(db, identity, site.realms)
        return identity
    user = await _account_for(db, identity, site.realms, client)
    if user is not None:
        return await _signed_in(db, user, label, client)
    if not signups_open:
        raise SignInRefused("no_account")
    return identity


async def _refuse_sso_domain(db: AsyncSession, identity: ProviderIdentity, realms: tuple[str, ...]) -> None:
    if PRACTICE_REALM not in realms:
        return
    user = await account_by_email(db, identity.email, realms)
    if user is not None and user.realm != PRACTICE_REALM:
        return
    try:
        await ensure_service_allowed(db, identity.email)
    except SsoRequired as error:
        raise SignInRefused("sso_required") from error


async def _note_refusal(db: AsyncSession, identity: ProviderIdentity, site: Site, detail: str, client: Client) -> None:
    user = await account_by_email(db, identity.email, site.realms)
    realm = site.realms[0] if len(site.realms) == 1 else None
    facts = AuthEventFacts(client, detail=detail, email=identity.email, realm=realm)
    await record_auth_event(db, SIGN_IN_FAILED, user, facts)
    await db.commit()


async def _refuse_foreign_subject(db: AsyncSession, identity: ProviderIdentity, realms: tuple[str, ...]) -> None:
    user = await account_by_email(db, identity.email, realms)
    bound = await db.scalar(
        select(UserIdentity.user_id)
        .where(
            UserIdentity.provider == identity.provider,
            UserIdentity.subject == identity.subject,
            UserIdentity.realm.in_(realms),
        )
        .limit(1)
    )
    if bound is not None and (user is None or bound != user.id):
        raise SignInRefused("mismatch")


async def _signed_in(db: AsyncSession, user: User, label: str, client: Client) -> Tokens | MfaChallenge:
    try:
        return await sign_in_user(db, user, method=label, client=client)
    except SignInRefused:
        raise
    except Unauthorized as error:
        raise SignInRefused("blocked") from error


async def admit(db: AsyncSession, user: User, identity: ProviderIdentity, client: Client) -> None:
    if user.status == "blocked":
        raise SignInRefused("blocked")
    await bind_identity(db, user, identity.provider, identity.subject)
    if user.status == "invited":
        await accept_invitations(db, user, client)
        user.status = "active"


async def bind_identity(db: AsyncSession, user: User, provider: str, subject: str) -> None:
    bound = await db.scalar(
        select(UserIdentity).where(UserIdentity.user_id == user.id, UserIdentity.provider == provider)
    )
    if bound is not None:
        if not hmac.compare_digest(bound.subject, subject):
            raise SignInRefused("mismatch")
        return
    if await _subject_bound(db, provider, subject, (user.realm,)):
        raise SignInRefused("mismatch")
    db.add(UserIdentity(user_id=user.id, realm=user.realm, provider=provider, subject=subject))


def _started(returned: ProviderReturn, provider: str, site: Site) -> dict[str, Any]:
    if not (returned.cookie and returned.state and returned.code):
        raise SignInRefused("failed")
    try:
        claims = read_token(returned.cookie, START_TOKEN)
    except TokenError as error:
        raise SignInRefused("failed") from error
    if claims.get("idp") != provider or claims.get("site") != site.url:
        raise SignInRefused("failed")
    if not hmac.compare_digest(str(claims["sub"]), returned.state):
        raise SignInRefused("failed")
    return claims


async def _identity(provider: IdentityProvider, code: str, started: dict[str, Any]) -> ProviderIdentity:
    if not provider.enabled:
        raise SignInRefused("failed")
    try:
        return await provider.identity(
            code,
            verifier=str(started["pkce"]),
            nonce=str(started["nonce"]),
            redirect_uri=callback_url(str(started["site"]), provider.name),
        )
    except UnverifiedEmail as error:
        raise SignInRefused("unverified_email") from error
    except (IdentityRefused, ProviderUnreachable) as error:
        raise SignInRefused("failed") from error


async def _account_for(
    db: AsyncSession, identity: ProviderIdentity, realms: tuple[str, ...], client: Client
) -> User | None:
    user = await account_by_email(db, identity.email, realms)
    if user is None:
        if await _subject_bound(db, identity.provider, identity.subject, realms):
            raise SignInRefused("mismatch")
        return None
    await admit(db, user, identity, client)
    await db.commit()
    return user


async def _subject_bound(db: AsyncSession, provider: str, subject: str, realms: tuple[str, ...]) -> bool:
    query = select(UserIdentity.id).where(
        UserIdentity.provider == provider, UserIdentity.subject == subject, UserIdentity.realm.in_(realms)
    )
    return await db.scalar(query.limit(1)) is not None
