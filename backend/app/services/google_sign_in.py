from __future__ import annotations

import hmac
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.google_oidc import GoogleIdentity, GoogleRefused, GoogleSignIn, GoogleUnreachable
from app.core.deps import ACTIVE_PRACTICE_STATUSES, ensure_practice_open
from app.core.errors import NotFound, Unauthorized
from app.core.security import TokenError, issue_token, random_token, read_token
from app.models import Practice, User
from app.services.auth import MfaChallenge, Tokens, sign_in_user
from app.services.rate_limits import GOOGLE_PER_IP, hit

START_MINUTES = 10
GOOGLE_METHOD = "Google"
START_TOKEN = "google_start"


class GoogleSignInRefused(Unauthorized):
    def __init__(self, reason: str) -> None:
        super().__init__(f"Google sign-in refused ({reason})")
        self.reason = reason


@dataclass(frozen=True)
class GoogleStart:
    url: str
    cookie: str


@dataclass(frozen=True)
class GoogleReturn:
    code: str | None
    state: str | None
    cookie: str | None


def start(google: GoogleSignIn) -> GoogleStart:
    if not google.enabled:
        raise NotFound("Google sign-in is not set up")
    state, nonce, verifier = random_token(), random_token(), random_token()
    cookie = issue_token(START_TOKEN, state, START_MINUTES, nonce=nonce, pkce=verifier)
    return GoogleStart(google.authorization_url(state=state, nonce=nonce, verifier=verifier), cookie)


async def finish(
    db: AsyncSession, google: GoogleSignIn, returned: GoogleReturn, *, ip: str | None, agent: str | None
) -> Tokens | MfaChallenge:
    await hit(db, GOOGLE_PER_IP, ip)
    started = _started(returned)
    identity = await _identity(google, returned.code or "", started)
    user = await _account_for(db, identity)
    return await sign_in_user(db, user, method=GOOGLE_METHOD, ip=ip, agent=agent)


def _started(returned: GoogleReturn) -> dict[str, Any]:
    if not (returned.cookie and returned.state and returned.code):
        raise GoogleSignInRefused("failed")
    try:
        claims = read_token(returned.cookie, START_TOKEN)
    except TokenError as error:
        raise GoogleSignInRefused("failed") from error
    if not hmac.compare_digest(str(claims["sub"]), returned.state):
        raise GoogleSignInRefused("failed")
    return claims


async def _identity(google: GoogleSignIn, code: str, started: dict[str, Any]) -> GoogleIdentity:
    if not google.enabled:
        raise GoogleSignInRefused("failed")
    try:
        return await google.identity(code, verifier=str(started["pkce"]), nonce=str(started["nonce"]))
    except (GoogleRefused, GoogleUnreachable) as error:
        raise GoogleSignInRefused("failed") from error


async def _account_for(db: AsyncSession, identity: GoogleIdentity) -> User:
    user = await db.scalar(select(User).where(User.email == identity.email.strip().lower()))
    if user is None:
        raise GoogleSignInRefused("no_account")
    practice = await db.get(Practice, user.practice_id) if user.practice_id else None
    if user.status == "blocked" or (practice is not None and practice.status not in ACTIVE_PRACTICE_STATUSES):
        raise GoogleSignInRefused("blocked")
    if practice is not None:
        ensure_practice_open(practice)
    await _bind(db, user, identity.sub)
    if user.status == "invited":
        user.status = "active"
    await db.commit()
    return user


async def _bind(db: AsyncSession, user: User, sub: str) -> None:
    if user.google_sub is not None:
        if not hmac.compare_digest(user.google_sub, sub):
            raise GoogleSignInRefused("mismatch")
        return
    if await db.scalar(select(User.id).where(User.google_sub == sub)):
        raise GoogleSignInRefused("mismatch")
    user.google_sub = sub
