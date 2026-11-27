from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Annotated
from weakref import WeakSet
from zoneinfo import ZoneInfo

from fastapi import Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.calendar import today_in, zone_named
from app.core.db import get_session
from app.core.errors import Forbidden, Unauthorized
from app.core.realms import request_site
from app.core.roles import HQ, HQ_ROLE, PLAN_MANAGERS
from app.core.security import TokenError, read_token
from app.models import HQ_REALM, Practice, PracticeMembership, User, utcnow

ACTIVE_PRACTICE_STATUSES = ("trial", "active")
ACTIVE_MEMBERSHIP = "active"
ACTIVITY_WRITE_INTERVAL = timedelta(minutes=1)
NO_ROLE = ""
SESSION_ENDED = "session ended"
PRACTICE_CLAIM = "prc"
ROLE_CLAIM = "rol"

Db = Annotated[AsyncSession, Depends(get_session)]
ROLE_GUARDS: WeakSet[Callable[..., Awaitable[Actor]]] = WeakSet()


@dataclass(frozen=True)
class Actor:
    user: User
    practice: Practice | None
    ip: str | None
    user_agent: str | None
    billing_only_since: date | None = None
    membership: PracticeMembership | None = None

    @property
    def role(self) -> str:
        return role_of(self.user, self.membership)

    @property
    def own_practice(self) -> Practice:
        if self.practice is None:
            raise Forbidden("this action needs a practice account")
        return self.practice

    @property
    def practice_id(self) -> str:
        return self.own_practice.id

    @property
    def zone(self) -> ZoneInfo:
        return zone_named(self.own_practice.time_zone)

    @property
    def client(self) -> Client:
        return Client(self.ip, self.user_agent)


@dataclass(frozen=True)
class Client:
    ip: str | None
    agent: str | None


@dataclass(frozen=True)
class ProviderActor:
    request_id: str
    provider_id: str
    practice_id: str
    ip: str | None
    user_agent: str | None


class PlanEnded(Forbidden):
    code = "plan_ended"

    def __init__(self, ended_on: date) -> None:
        super().__init__(f"This practice's plan ended on {ended_on.isoformat()}")


def plan_ended_on(practice: Practice | None) -> date | None:
    if practice is None or practice.renews_on is None:
        return None
    return practice.renews_on if practice.renews_on < today_in(zone_named(practice.time_zone)) else None


@dataclass(frozen=True)
class PracticeAccess:
    practice: Practice | None
    membership: PracticeMembership | None

    @property
    def role(self) -> str:
        return self.membership.role if self.membership is not None else HQ_ROLE

    @property
    def practice_id(self) -> str | None:
        return self.practice.id if self.practice is not None else None


HQ_ACCESS = PracticeAccess(None, None)


def role_of(user: User, membership: PracticeMembership | None) -> str:
    if membership is not None:
        return membership.role
    return HQ_ROLE if user.realm == HQ_REALM else NO_ROLE


def ensure_session_allowed(role: str, practice: Practice | None) -> None:
    if role in HQ:
        return
    if practice is None or practice.status not in ACTIVE_PRACTICE_STATUSES:
        raise Unauthorized("your practice is not active")
    ended_on = plan_ended_on(practice)
    if ended_on is not None and role not in PLAN_MANAGERS:
        raise PlanEnded(ended_on)


def billing_only_since(role: str, practice: Practice | None) -> date | None:
    return None if role in HQ else plan_ended_on(practice)


def needs_two_step(access: PracticeAccess) -> bool:
    if access.role in HQ:
        return True
    return access.practice is not None and access.role in access.practice.mfa_roles


async def active_membership(db: AsyncSession, user_id: str, practice_id: str) -> PracticeMembership | None:
    return await db.scalar(
        select(PracticeMembership).where(
            PracticeMembership.user_id == user_id,
            PracticeMembership.practice_id == practice_id,
            PracticeMembership.status == ACTIVE_MEMBERSHIP,
            PracticeMembership.ended_at.is_(None),
        )
    )


async def practice_access(db: AsyncSession, user: User, practice_id: str | None) -> PracticeAccess:
    if user.realm == HQ_REALM:
        return HQ_ACCESS
    membership = await active_membership(db, user.id, practice_id) if practice_id else None
    if membership is None:
        raise Unauthorized(SESSION_ENDED)
    practice = await db.get_one(Practice, membership.practice_id)
    ensure_session_allowed(membership.role, practice)
    return PracticeAccess(practice, membership)


def bearer(authorization: str | None) -> str:
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise Unauthorized("sign in required")
    return token


async def session_actor(request: Request, db: Db, authorization: Annotated[str | None, Header()] = None) -> Actor:
    try:
        claims = read_token(bearer(authorization), "access")
    except TokenError as error:
        raise Unauthorized("session expired") from error
    user = await db.get(User, claims["sub"])
    if user is None or user.status != "active" or user.token_version != claims.get("ver"):
        raise Unauthorized(SESSION_ENDED)
    if user.realm not in request_site(request).realms:
        raise Unauthorized(SESSION_ENDED)
    access = await practice_access(db, user, claims.get(PRACTICE_CLAIM))
    if access.role != claims.get(ROLE_CLAIM):
        raise Unauthorized(SESSION_ENDED)
    now = utcnow()
    if user.last_active_at is None or now - user.last_active_at > ACTIVITY_WRITE_INTERVAL:
        user.last_active_at = now
        await db.commit()
    ip = request.client.host if request.client else None
    since = billing_only_since(access.role, access.practice)
    return Actor(user, access.practice, ip, request.headers.get("user-agent"), since, access.membership)


async def current_actor(actor: Annotated[Actor, Depends(session_actor)]) -> Actor:
    if actor.billing_only_since is not None:
        raise PlanEnded(actor.billing_only_since)
    return actor


def require(*roles: str) -> Callable[..., Awaitable[Actor]]:
    async def guard(actor: Annotated[Actor, Depends(current_actor)]) -> Actor:
        return _in_role(actor, roles)

    ROLE_GUARDS.add(guard)
    return guard


def require_for_billing(*roles: str) -> Callable[..., Awaitable[Actor]]:
    async def guard(actor: Annotated[Actor, Depends(session_actor)]) -> Actor:
        return _in_role(actor, roles)

    ROLE_GUARDS.add(guard)
    return guard


def _in_role(actor: Actor, roles: tuple[str, ...]) -> Actor:
    if actor.role not in roles:
        raise Forbidden("your role cannot do this")
    return actor


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
