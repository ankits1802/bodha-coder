from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.messenger import Messenger
from app.core.config import get_settings
from app.core.deps import Actor, Client
from app.core.errors import Conflict, Forbidden, NotFound
from app.core.realms import realm_url
from app.core.roles import INVITABLE_ROLES
from app.models import PRACTICE_REALM, Practice, PracticeMembership, User, utcnow
from app.services.account_lookup import account_by_email, email_in_use, normal_email
from app.services.audit_log import record_access, record_activity, record_practice_access
from app.services.auth import issue_user_token
from app.services.auth_events import AuthEventFacts, record_auth_event
from app.services.memberships import (
    ACTIVE,
    BLOCKED,
    INVITED,
    LIVE,
    enrol,
    ensure_admin_remains,
    membership_in,
    retire_legacy_link,
)
from app.services.password_reset import send_reset_email
from app.services.plan_limits import ensure_user_room
from app.services.recovery_codes import clear_recovery_codes
from app.services.two_step import forget_two_step
from app.services.user_sessions import end_all_sessions, end_practice_sessions

__all__ = [
    "ALREADY_MEMBER",
    "EMAIL_TAKEN",
    "Arrival",
    "Member",
    "Newcomer",
    "bring_in",
    "change_role",
    "invite",
    "remove_member",
    "resend_invite",
    "reset_mfa",
    "send_invite",
    "send_password_reset",
    "team",
    "update_member",
]

EMAIL_TAKEN = "someone already uses that email"
ALREADY_MEMBER = "this person is already on the team"
OWN_ACCESS = "you can't change your own access"
OTHER_PRACTICES = "this person also works in another practice; they reset two-step with a recovery code"
MEMBER_INVITED = "member invited"
MEMBER_ADDED = "member added"
ROLE_CHANGED = "member role changed"
MEMBER_BLOCKED = "member blocked"
MEMBER_UNBLOCKED = "member unblocked"
MEMBER_REMOVED = "member removed"


@dataclass(frozen=True)
class Member:
    person: User
    membership: PracticeMembership


@dataclass(frozen=True)
class Newcomer:
    name: str
    email: str
    role: str


@dataclass(frozen=True)
class Arrival:
    person: User
    membership: PracticeMembership
    invited: bool


async def team(db: AsyncSession, actor: Actor) -> list[Member]:
    rows = await db.execute(
        select(User, PracticeMembership)
        .join(PracticeMembership, PracticeMembership.user_id == User.id)
        .where(PracticeMembership.practice_id == actor.practice_id, LIVE)
        .order_by(User.name, User.id)
    )
    return [Member(person, membership) for person, membership in rows.tuples()]


async def invite(db: AsyncSession, messenger: Messenger, actor: Actor, *, name: str, email: str, role: str) -> User:
    if role not in INVITABLE_ROLES:
        raise Forbidden("that role cannot be invited")
    arrival = await bring_in(db, messenger, actor.own_practice, Newcomer(name, email, role), by=actor.user)
    action = MEMBER_INVITED if arrival.invited else MEMBER_ADDED
    record_access(db, actor, action, detail=f"{arrival.person.name} as {role}")
    await db.commit()
    return arrival.person


async def bring_in(
    db: AsyncSession, messenger: Messenger, practice: Practice, newcomer: Newcomer, *, by: User
) -> Arrival:
    address = normal_email(newcomer.email)
    person = await account_by_email(db, address, (PRACTICE_REALM,))
    if person is None and await email_in_use(db, address, PRACTICE_REALM):
        raise Conflict(EMAIL_TAKEN)
    current = await membership_in(db, person.id, practice.id) if person is not None else None
    if current is not None and current.ended_at is None:
        raise Conflict(ALREADY_MEMBER)
    await ensure_user_room(db, practice)
    if person is None:
        person = User(email=address, name=newcomer.name.strip(), role=newcomer.role, status=INVITED)
        db.add(person)
        await db.flush()
    membership = await enrol(db, person, practice.id, newcomer.role, invited_by=by.id)
    if person.status == INVITED:
        await send_invite(db, messenger, person, team_name=practice.name)
    else:
        await send_added(messenger, person, practice_name=practice.name)
    return Arrival(person, membership, person.status == INVITED)


async def send_invite(db: AsyncSession, messenger: Messenger, user: User, *, team_name: str) -> None:
    token = await issue_user_token(db, user, "invite")
    link = f"{realm_url(user.realm)}/set-password#{token}"
    await messenger.email(
        user.email,
        subject=f"Join {team_name} on Bodha Assure",
        body=f"{user.name}, you have been invited to Bodha Assure. Set your password: {link}",
    )


async def send_added(messenger: Messenger, user: User, *, practice_name: str) -> None:
    await messenger.email(
        user.email,
        subject=f"You've been added to {practice_name}",
        body=(
            f"{user.name}, you have been added to {practice_name} on Bodha Assure. "
            f"Sign in: {get_settings().app_url}/sign-in"
        ),
    )


async def member(db: AsyncSession, actor: Actor, user_id: str) -> Member:
    person = await db.get(User, user_id)
    membership = await membership_in(db, user_id, actor.practice_id) if person is not None else None
    if person is None or membership is None or membership.ended_at is not None:
        raise NotFound("member not found")
    return Member(person, membership)


async def update_member(
    db: AsyncSession, actor: Actor, user_id: str, *, role: str | None, blocked: bool | None
) -> None:
    if user_id == actor.user.id:
        raise Forbidden(OWN_ACCESS)
    found = await member(db, actor, user_id)
    if role is not None and role != found.membership.role:
        await change_role(db, found, role, by=actor.user, client=actor.client)
    if blocked is True and found.membership.status != BLOCKED:
        await _block(db, actor, found)
    if blocked is False and found.membership.status == BLOCKED:
        await _unblock(db, actor, found)
    await db.commit()


async def change_role(db: AsyncSession, found: Member, role: str, *, by: User, client: Client) -> None:
    if role not in INVITABLE_ROLES:
        raise Forbidden("that role cannot be given")
    membership = found.membership
    if role != membership.role:
        await ensure_admin_remains(db, membership)
    detail = f"{found.person.name}: {membership.role} to {role}"
    membership.role = role
    retire_legacy_link(found.person)
    record_practice_access(db, membership.practice_id, by, ROLE_CHANGED, detail=detail, client=client)


async def _block(db: AsyncSession, actor: Actor, found: Member) -> None:
    await ensure_admin_remains(db, found.membership)
    found.membership.status = BLOCKED
    retire_legacy_link(found.person)
    await end_practice_sessions(db, found.person, actor.practice_id, reason=MEMBER_BLOCKED, client=actor.client)
    record_access(db, actor, MEMBER_BLOCKED, detail=found.person.name)


async def _unblock(db: AsyncSession, actor: Actor, found: Member) -> None:
    await ensure_user_room(db, actor.own_practice)
    found.membership.status = ACTIVE if found.person.status == ACTIVE else INVITED
    retire_legacy_link(found.person)
    record_access(db, actor, MEMBER_UNBLOCKED, detail=found.person.name)


async def remove_member(db: AsyncSession, actor: Actor, user_id: str) -> None:
    if user_id == actor.user.id:
        raise Forbidden(OWN_ACCESS)
    found = await member(db, actor, user_id)
    await ensure_admin_remains(db, found.membership)
    found.membership.ended_at = utcnow()
    retire_legacy_link(found.person)
    await end_practice_sessions(db, found.person, actor.practice_id, reason=MEMBER_REMOVED, client=actor.client)
    record_access(db, actor, MEMBER_REMOVED, detail=f"{found.person.name}, {found.membership.role}")
    await db.commit()


async def reset_mfa(db: AsyncSession, actor: Actor, user_id: str) -> None:
    found = await member(db, actor, user_id)
    if await _practices_counted(db, user_id) > 1:
        raise Conflict(OTHER_PRACTICES)
    person = found.person
    forget_two_step(person)
    await clear_recovery_codes(db, person)
    await record_auth_event(db, "two_step_off", person, AuthEventFacts(actor.client, detail=f"by {actor.user.name}"))
    await end_all_sessions(db, person, reason="two-step reset", client=actor.client)
    record_activity(db, actor, "two-step reset", practice_id=actor.practice_id, detail=person.name)
    await db.commit()


async def _practices_counted(db: AsyncSession, user_id: str) -> int:
    count = await db.scalar(
        select(func.count()).select_from(PracticeMembership).where(PracticeMembership.user_id == user_id, LIVE)
    )
    return count or 0


async def send_password_reset(db: AsyncSession, messenger: Messenger, actor: Actor, user_id: str) -> None:
    found = await member(db, actor, user_id)
    if found.membership.status == BLOCKED:
        raise Conflict("unblock this member before resetting their password")
    await send_reset_email(db, messenger, found.person)
    record_activity(db, actor, "password reset sent", practice_id=actor.practice_id, detail=found.person.name)
    await db.commit()


async def resend_invite(db: AsyncSession, messenger: Messenger, actor: Actor, user_id: str) -> None:
    found = await member(db, actor, user_id)
    if found.membership.status != INVITED or found.person.status != INVITED:
        raise Conflict("only pending invitations can be resent")
    await send_invite(db, messenger, found.person, team_name=actor.own_practice.name)
    await db.commit()
