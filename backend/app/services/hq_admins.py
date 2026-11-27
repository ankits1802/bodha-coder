from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.messenger import Messenger
from app.core.deps import Actor
from app.core.errors import Conflict, NotFound
from app.core.roles import ADMIN_ROLE, ADMINS
from app.models import CLOSED_STATUSES, PRACTICE_REALM, Practice, PracticeMembership, User
from app.services.account_lookup import account_by_email
from app.services.audit_log import record_activity, record_practice_access
from app.services.memberships import ACTIVE, BLOCKED, INVITED, active_members, membership_in, retire_legacy_link
from app.services.plan_limits import ensure_user_room
from app.services.team import Member, Newcomer, bring_in, change_role

__all__ = ["APPOINTED", "OUTCOMES", "Appointment", "appoint_admin"]

APPOINTED = "admin appointed by HQ"
INVITED_OUTCOME = "invited"
ADDED_OUTCOME = "added"
PROMOTED_OUTCOME = "promoted"
OUTCOMES = (INVITED_OUTCOME, ADDED_OUTCOME, PROMOTED_OUTCOME)
ALREADY_ADMIN = "this person is already an admin of the practice"
CLOSED_PRACTICE = "a closed practice takes no new admins"


@dataclass(frozen=True)
class Appointment:
    name: str
    email: str
    reason: str


async def appoint_admin(
    db: AsyncSession, messenger: Messenger, actor: Actor, practice_id: str, appointment: Appointment
) -> str:
    practice = await db.get(Practice, practice_id, with_for_update=True)
    if practice is None:
        raise NotFound("practice not found")
    if practice.status in CLOSED_STATUSES:
        raise Conflict(CLOSED_PRACTICE)
    person = await account_by_email(db, appointment.email, (PRACTICE_REALM,))
    current = await membership_in(db, person.id, practice.id) if person is not None else None
    if person is not None and current is not None and current.ended_at is None:
        outcome = await _promote(db, actor, practice, Member(person, current))
    else:
        newcomer = Newcomer(appointment.name, appointment.email, ADMIN_ROLE)
        arrival = await bring_in(db, messenger, practice, newcomer, by=actor.user)
        person, outcome = arrival.person, INVITED_OUTCOME if arrival.invited else ADDED_OUTCOME
    detail = f"{person.name}: {appointment.reason}"
    record_activity(db, actor, APPOINTED, practice_id=practice.id, detail=detail)
    record_practice_access(db, practice.id, actor.user, APPOINTED, detail=detail, client=actor.client)
    await db.flush()
    await _tell_admins(db, messenger, practice, person)
    await db.commit()
    return outcome


async def _promote(db: AsyncSession, actor: Actor, practice: Practice, found: Member) -> str:
    membership: PracticeMembership = found.membership
    if membership.role == ADMIN_ROLE and membership.status == ACTIVE:
        raise Conflict(ALREADY_ADMIN)
    if membership.status == BLOCKED:
        await ensure_user_room(db, practice)
        membership.status = ACTIVE if found.person.status == ACTIVE else INVITED
        retire_legacy_link(found.person)
    if membership.role != ADMIN_ROLE:
        await change_role(db, found, ADMIN_ROLE, by=actor.user, client=actor.client)
    return PROMOTED_OUTCOME


async def _tell_admins(db: AsyncSession, messenger: Messenger, practice: Practice, person: User) -> None:
    others = active_members(practice.id, User.email, roles=ADMINS).where(User.id != person.id).order_by(User.email)
    for email in (await db.scalars(others)).all():
        await messenger.email(
            email,
            subject=f"New admin at {practice.name}",
            body=f"Bodha HQ added {person.name} as an admin of {practice.name} on Bodha Assure.",
        )
