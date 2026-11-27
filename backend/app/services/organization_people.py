from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.messenger import Messenger
from app.core.config import get_settings
from app.core.deps import ACTIVE_PRACTICE_STATUSES, Actor
from app.core.errors import Conflict, Forbidden, Invalid
from app.core.roles import ADMINS, INVITABLE_ROLES
from app.models import PRACTICE_REALM, Organization, Practice, PracticeMembership, User
from app.services.account_lookup import account_by_email, email_in_use, normal_email
from app.services.audit_log import record_activity, record_practice_access
from app.services.memberships import INVITED, active_members, enrol, membership_in
from app.services.organizations import organization_practice
from app.services.plan_limits import ensure_user_room
from app.services.team import EMAIL_TAKEN, MEMBER_ADDED, MEMBER_INVITED, send_invite

__all__ = ["ACCESS_GRANTED", "Placement", "add_person", "grant_own_access"]

ACCESS_GRANTED = "access granted by organization admin"
NOT_OPEN = "{name} is not open"
ALREADY_THERE = "this person is already on the team of {name}"
ALREADY_YOURS = "you are already on the team of {name}"


@dataclass(frozen=True)
class Placement:
    practice_id: str
    role: str


async def add_person(
    db: AsyncSession,
    messenger: Messenger,
    actor: Actor,
    organization: Organization,
    *,
    name: str,
    email: str,
    placements: list[Placement],
) -> User:
    practices = await _placed_practices(db, organization, placements)
    address = normal_email(email)
    person = await account_by_email(db, address, (PRACTICE_REALM,))
    if person is None and await email_in_use(db, address, PRACTICE_REALM):
        raise Conflict(EMAIL_TAKEN)
    for practice in practices:
        await _refuse_member(db, person, practice, ALREADY_THERE)
        await ensure_user_room(db, practice)
    if person is None:
        person = User(email=address, name=name.strip(), role=placements[0].role, status=INVITED)
        db.add(person)
        await db.flush()
    for practice, placement in zip(practices, placements, strict=True):
        await enrol(db, person, practice.id, placement.role, invited_by=actor.user.id)
        action = MEMBER_INVITED if person.status == INVITED else MEMBER_ADDED
        detail = f"{person.name} as {placement.role}, from {organization.name}"
        record_practice_access(db, practice.id, actor.user, action, detail=detail, client=actor.client)
    if person.status == INVITED:
        await send_invite(db, messenger, person, team_name=organization.name)
    else:
        await _send_added(messenger, person, [practice.name for practice in practices])
    await db.commit()
    return person


async def _placed_practices(
    db: AsyncSession, organization: Organization, placements: list[Placement]
) -> list[Practice]:
    if not placements or len({placement.practice_id for placement in placements}) != len(placements):
        raise Invalid("choose each practice once")
    practices = []
    for placement in placements:
        if placement.role not in INVITABLE_ROLES:
            raise Forbidden("that role cannot be given")
        practice = await organization_practice(db, organization, placement.practice_id)
        if practice.status not in ACTIVE_PRACTICE_STATUSES:
            raise Conflict(NOT_OPEN.format(name=practice.name))
        practices.append(practice)
    return practices


async def _refuse_member(db: AsyncSession, person: User | None, practice: Practice, message: str) -> None:
    current = await membership_in(db, person.id, practice.id) if person is not None else None
    if current is not None and current.ended_at is None:
        raise Conflict(message.format(name=practice.name))


async def _send_added(messenger: Messenger, person: User, practice_names: list[str]) -> None:
    listed = ", ".join(practice_names)
    await messenger.email(
        person.email,
        subject=f"You've been added to {listed}",
        body=(
            f"{person.name}, you have been added to {listed} on Bodha Assure. Sign in: {get_settings().app_url}/sign-in"
        ),
    )


async def grant_own_access(
    db: AsyncSession,
    messenger: Messenger,
    actor: Actor,
    organization: Organization,
    practice_id: str,
    *,
    role: str,
    reason: str,
) -> PracticeMembership:
    if role not in INVITABLE_ROLES:
        raise Forbidden("that role cannot be given")
    practice = await organization_practice(db, organization, practice_id)
    if practice.status not in ACTIVE_PRACTICE_STATUSES:
        raise Conflict(NOT_OPEN.format(name=practice.name))
    await _refuse_member(db, actor.user, practice, ALREADY_YOURS)
    await ensure_user_room(db, practice)
    membership = await enrol(db, actor.user, practice.id, role, invited_by=actor.user.id)
    detail = f"{actor.user.name} as {role}, {organization.name}: {reason}"
    record_practice_access(db, practice.id, actor.user, ACCESS_GRANTED, detail=detail, client=actor.client)
    record_activity(db, actor, ACCESS_GRANTED, practice_id=practice.id, detail=detail)
    await db.flush()
    await _tell_admins(db, messenger, practice, actor.user, organization)
    await db.commit()
    return membership


async def _tell_admins(
    db: AsyncSession, messenger: Messenger, practice: Practice, person: User, organization: Organization
) -> None:
    others = active_members(practice.id, User.email, roles=ADMINS).where(User.id != person.id).order_by(User.email)
    for email in (await db.scalars(others)).all():
        await messenger.email(
            email,
            subject=f"Organization access to {practice.name}",
            body=(
                f"{person.name}, an admin of {organization.name}, gave themselves access to {practice.name} "
                "on Bodha Assure. The access log of the practice shows the reason."
            ),
        )
