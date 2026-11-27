from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import HQ_ACCESS, Client, PracticeAccess, ensure_session_allowed
from app.core.errors import Conflict, Forbidden, NotFound, Unauthorized
from app.core.roles import ADMINS
from app.models import HQ_REALM, Practice, PracticeMembership, User, utcnow
from app.services.audit_log import record_practice_access
from app.services.user_sessions import end_practice_sessions

__all__ = [
    "ACTIVE",
    "BLOCKED",
    "INVITED",
    "LAST_ADMIN",
    "LIVE",
    "SEAT_HOLDING",
    "PracticeChoice",
    "accept_invitations",
    "active_members",
    "enrol",
    "ensure_admin_remains",
    "landing_access",
    "leave_practice",
    "live_membership",
    "member_names",
    "membership_in",
    "practices_of",
    "reopen_person",
    "retire_legacy_link",
]

ACTIVE = "active"
INVITED = "invited"
BLOCKED = "blocked"
SEAT_STATUSES = (INVITED, ACTIVE)
LAST_ADMIN = "a practice needs at least one active admin"
NO_PRACTICE = "you have no active practice"
NOT_FOUND = "member not found"
INVITE_ACCEPTED = "invite accepted"
MEMBER_LEFT = "member left"
LIVE = PracticeMembership.ended_at.is_(None)
SEAT_HOLDING = (LIVE, PracticeMembership.status.in_(SEAT_STATUSES))
ACTIVE_MEMBER = (LIVE, PracticeMembership.status == ACTIVE)


@dataclass(frozen=True)
class PracticeChoice:
    id: str
    name: str
    role: str


def active_members(practice_id: str, *columns: Any, roles: tuple[str, ...] | None = None) -> Select[Any]:
    query = (
        select(*columns)
        .select_from(User)
        .join(PracticeMembership, PracticeMembership.user_id == User.id)
        .where(PracticeMembership.practice_id == practice_id, *ACTIVE_MEMBER, User.status == ACTIVE)
    )
    return query if roles is None else query.where(PracticeMembership.role.in_(roles))


async def member_names(db: AsyncSession, practice_id: str) -> dict[str, str]:
    rows = await db.execute(
        select(User.id, User.name)
        .join(PracticeMembership, PracticeMembership.user_id == User.id)
        .where(PracticeMembership.practice_id == practice_id)
    )
    return dict(rows.tuples().all())


async def membership_in(db: AsyncSession, user_id: str, practice_id: str) -> PracticeMembership | None:
    return await db.scalar(
        select(PracticeMembership).where(
            PracticeMembership.user_id == user_id, PracticeMembership.practice_id == practice_id
        )
    )


async def live_membership(db: AsyncSession, user_id: str, practice_id: str) -> PracticeMembership:
    found = await membership_in(db, user_id, practice_id)
    if found is None or found.ended_at is not None:
        raise NotFound(NOT_FOUND)
    return found


async def practices_of(db: AsyncSession, user: User) -> list[PracticeChoice]:
    if user.realm == HQ_REALM:
        return []
    rows = await db.execute(
        select(Practice.id, Practice.name, PracticeMembership.role)
        .join(PracticeMembership, PracticeMembership.practice_id == Practice.id)
        .where(PracticeMembership.user_id == user.id, *ACTIVE_MEMBER)
        .order_by(Practice.name, Practice.id)
    )
    return [PracticeChoice(practice_id, name, role) for practice_id, name, role in rows.tuples()]


async def landing_access(db: AsyncSession, user: User) -> PracticeAccess:
    if user.realm == HQ_REALM:
        return HQ_ACCESS
    order: list[Any] = [PracticeMembership.created_at, PracticeMembership.id]
    if user.last_practice_id:
        order.insert(0, (PracticeMembership.practice_id == user.last_practice_id).desc())
    rows = (
        await db.execute(
            select(PracticeMembership, Practice)
            .join(Practice, Practice.id == PracticeMembership.practice_id)
            .where(PracticeMembership.user_id == user.id, *ACTIVE_MEMBER)
            .order_by(*order)
        )
    ).all()
    if not rows:
        raise Unauthorized(NO_PRACTICE)
    for membership, practice in rows:
        if _session_allowed(membership.role, practice):
            return PracticeAccess(practice, membership)
    ensure_session_allowed(rows[0][0].role, rows[0][1])
    raise Unauthorized(NO_PRACTICE)


def _session_allowed(role: str, practice: Practice) -> bool:
    try:
        ensure_session_allowed(role, practice)
    except (Unauthorized, Forbidden):
        return False
    return True


async def ensure_admin_remains(db: AsyncSession, membership: PracticeMembership) -> None:
    if membership.role not in ADMINS or membership.status != ACTIVE or membership.ended_at is not None:
        return
    admins = await db.scalars(
        select(PracticeMembership.id)
        .where(
            PracticeMembership.practice_id == membership.practice_id,
            PracticeMembership.role.in_(ADMINS),
            *ACTIVE_MEMBER,
        )
        .with_for_update()
    )
    if not any(found != membership.id for found in admins.all()):
        raise Conflict(LAST_ADMIN)


async def accept_invitations(db: AsyncSession, user: User, client: Client) -> list[PracticeMembership]:
    invited = list(
        await db.scalars(
            select(PracticeMembership).where(
                PracticeMembership.user_id == user.id, PracticeMembership.status == INVITED, LIVE
            )
        )
    )
    for membership in invited:
        membership.status = ACTIVE
        record_practice_access(db, membership.practice_id, user, INVITE_ACCEPTED, detail=membership.role, client=client)
    return invited


async def enrol(
    db: AsyncSession, person: User, practice_id: str, role: str, *, invited_by: str | None
) -> PracticeMembership:
    reopen_person(person)
    status = ACTIVE if person.status == ACTIVE else INVITED
    membership = await membership_in(db, person.id, practice_id)
    if membership is None:
        membership = PracticeMembership(user_id=person.id, practice_id=practice_id)
        db.add(membership)
    membership.role, membership.status, membership.ended_at = role, status, None
    membership.invited_by = invited_by
    retire_legacy_link(person)
    await db.flush()
    return membership


async def leave_practice(db: AsyncSession, user: User, practice_id: str, *, client: Client) -> None:
    membership = await live_membership(db, user.id, practice_id)
    await ensure_admin_remains(db, membership)
    membership.ended_at = utcnow()
    retire_legacy_link(user)
    await end_practice_sessions(db, user, practice_id, reason=MEMBER_LEFT, client=client)
    record_practice_access(db, practice_id, user, MEMBER_LEFT, detail=membership.role, client=client)
    await db.commit()


def reopen_person(person: User) -> None:
    if person.status == BLOCKED:
        person.status = ACTIVE if person.password_hash else INVITED


def retire_legacy_link(person: User) -> None:
    person.legacy_practice_id = None
