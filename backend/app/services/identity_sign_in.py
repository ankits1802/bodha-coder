from __future__ import annotations

import hmac
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.oidc import IdentityProvider, ProviderIdentity, callback_url
from app.adapters.oidc_providers import IdentityRefused, ProviderUnreachable, UnverifiedEmail
from app.core.config import get_settings
from app.core.deps import ACTIVE_PRACTICE_STATUSES, ensure_session_allowed
from app.core.errors import NotFound, Unauthorized
from app.core.realms import Site
from app.core.security import TokenError, issue_token, random_token, read_token
from app.models import Practice, User, UserIdentity
from app.services.account_lookup import account_by_email
from app.services.auth import MfaChallenge, Tokens, sign_in_user
from app.services.rate_limits import IDENTITY_PER_IP, hit

START_MINUTES = 10
START_TOKEN = "oidc_start"


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


async def start(provider: IdentityProvider, site: Site) -> ProviderStart:
    if not provider.enabled:
        raise NotFound(f"{provider.label} sign-in is not set up")
    state, nonce, verifier = random_token(), random_token(), random_token()
    claims = {"nonce": nonce, "pkce": verifier, "idp": provider.name, "site": site.url}
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
    ip: str | None,
    agent: str | None,
) -> Tokens | MfaChallenge | ProviderIdentity:
    await hit(db, IDENTITY_PER_IP, ip)
    started = _started(returned, provider.name, site)
    identity = await _identity(provider, returned.code or "", started)
    user = await _account_for(db, identity, site.realms)
    if user is not None:
        return await sign_in_user(db, user, method=provider.label, ip=ip, agent=agent)
    if not (get_settings().self_signup_enabled and site.takes_signups):
        raise SignInRefused("no_account")
    return identity


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


async def _account_for(db: AsyncSession, identity: ProviderIdentity, realms: tuple[str, ...]) -> User | None:
    user = await account_by_email(db, identity.email, realms)
    if user is None:
        if await _subject_bound(db, identity.provider, identity.subject, realms):
            raise SignInRefused("mismatch")
        return None
    practice = await db.get(Practice, user.practice_id) if user.practice_id else None
    if user.status == "blocked" or (practice is not None and practice.status not in ACTIVE_PRACTICE_STATUSES):
        raise SignInRefused("blocked")
    if practice is not None:
        ensure_session_allowed(user, practice)
    await bind_identity(db, user, identity.provider, identity.subject)
    if user.status == "invited":
        user.status = "active"
    await db.commit()
    return user


async def _subject_bound(db: AsyncSession, provider: str, subject: str, realms: tuple[str, ...]) -> bool:
    query = select(UserIdentity.id).where(
        UserIdentity.provider == provider, UserIdentity.subject == subject, UserIdentity.realm.in_(realms)
    )
    return await db.scalar(query.limit(1)) is not None
