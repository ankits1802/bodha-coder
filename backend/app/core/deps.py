from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import timedelta
from typing import Annotated

from fastapi import Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.errors import Forbidden, Unauthorized
from app.core.security import TokenError, read_token
from app.models import Practice, User, utcnow

ACTIVE_PRACTICE_STATUSES = ("trial", "active")
ACTIVITY_WRITE_INTERVAL = timedelta(minutes=1)

Db = Annotated[AsyncSession, Depends(get_session)]


@dataclass(frozen=True)
class Actor:
    user: User
    practice: Practice | None
    ip: str | None
    user_agent: str | None

    @property
    def practice_id(self) -> str:
        if self.practice is None:
            raise Forbidden("this action needs a practice account")
        return self.practice.id


@dataclass(frozen=True)
class ProviderActor:
    request_id: str
    provider_id: str
    practice_id: str
    ip: str | None
    user_agent: str | None


def bearer(authorization: str | None) -> str:
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise Unauthorized("sign in required")
    return token


async def current_actor(request: Request, db: Db, authorization: Annotated[str | None, Header()] = None) -> Actor:
    try:
        claims = read_token(bearer(authorization), "access")
    except TokenError as error:
        raise Unauthorized("session expired") from error
    user = await db.get(User, claims["sub"])
    if user is None or user.status != "active" or user.token_version != claims.get("ver"):
        raise Unauthorized("session ended")
    practice = await db.get(Practice, user.practice_id) if user.practice_id else None
    if user.role != "hq" and (practice is None or practice.status not in ACTIVE_PRACTICE_STATUSES):
        raise Unauthorized("practice is not active")
    now = utcnow()
    if user.last_active_at is None or now - user.last_active_at > ACTIVITY_WRITE_INTERVAL:
        user.last_active_at = now
        await db.commit()
    return Actor(user, practice, request.client.host if request.client else None, request.headers.get("user-agent"))


def require(*roles: str) -> Callable[..., Awaitable[Actor]]:
    async def guard(actor: Annotated[Actor, Depends(current_actor)]) -> Actor:
        if actor.user.role not in roles:
            raise Forbidden("your role cannot do this")
        return actor

    return guard


async def current_provider(request: Request, authorization: Annotated[str | None, Header()] = None) -> ProviderActor:
    try:
        claims = read_token(bearer(authorization), "provider")
    except TokenError as error:
        raise Unauthorized("verification expired") from error
    return ProviderActor(
        claims["req"],
        claims["sub"],
        claims["prc"],
        request.client.host if request.client else None,
        request.headers.get("user-agent"),
    )
