from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.messenger import Messenger
from app.core.deps import Actor
from app.core.errors import Conflict, Forbidden, NotFound
from app.core.roles import HQ_ROLE
from app.models import HQ_REALM, User
from app.services.account_lookup import account_by_email, email_in_use, normal_email
from app.services.audit_log import record_activity
from app.services.team import EMAIL_TAKEN, send_invite
from app.services.user_sessions import end_all_sessions

__all__ = [
    "HQ_TEAM_NAME",
    "HqEnrolment",
    "deactivate_hq_member",
    "enrol_hq_person",
    "hq_team",
    "invite_hq_member",
    "reactivate_hq_member",
    "resend_hq_invite",
]

HQ_TEAM_NAME = "Bodha HQ"
INVITED = "hq member invited"
INVITE_RESENT = "hq invite resent"
DEACTIVATED = "hq member deactivated"
REACTIVATED = "hq member reactivated"
RENAMED = "hq member renamed"
LAST_ACTIVE = "keep at least one active HQ account"
ENROLMENT_OUTCOMES = {"invited": "invite sent again", "active": "already active", "blocked": "deactivated"}


@dataclass(frozen=True)
class HqEnrolment:
    user: User
    outcome: str
    renamed_from: str | None = None


async def hq_team(db: AsyncSession) -> list[User]:
    return list((await db.scalars(select(User).where(User.realm == HQ_REALM).order_by(User.name, User.id))).all())


async def invite_hq_member(
    db: AsyncSession, messenger: Messenger, actor: Actor | None, *, name: str, email: str
) -> User:
    if await email_in_use(db, email, HQ_REALM):
        raise Conflict(EMAIL_TAKEN)
    user = User(email=normal_email(email), name=name.strip(), role=HQ_ROLE, status="invited")
    db.add(user)
    await db.flush()
    await send_invite(db, messenger, user, team_name=HQ_TEAM_NAME)
    record_activity(db, actor, INVITED, practice_id=None, detail=user.name)
    await db.commit()
    return user


async def resend_hq_invite(db: AsyncSession, messenger: Messenger, actor: Actor | None, user_id: str) -> None:
    user = await _hq_member(db, user_id)
    if user.status != "invited":
        raise Conflict("only pending invitations can be resent")
    await send_invite(db, messenger, user, team_name=HQ_TEAM_NAME)
    record_activity(db, actor, INVITE_RESENT, practice_id=None, detail=user.name)
    await db.commit()


async def deactivate_hq_member(db: AsyncSession, actor: Actor, user_id: str) -> None:
    if user_id == actor.user.id:
        raise Forbidden("you can't change your own access")
    locked = select(User).where(User.realm == HQ_REALM).with_for_update().execution_options(populate_existing=True)
    team = list((await db.scalars(locked)).all())
    user = next((member for member in team if member.id == user_id), None)
    if user is None:
        raise NotFound("member not found")
    if user.status == "blocked":
        return
    if user.status == "active" and not any(other.status == "active" for other in team if other.id != user.id):
        raise Conflict(LAST_ACTIVE)
    user.status = "blocked"
    await end_all_sessions(db, user, reason=DEACTIVATED, client=actor.client)
    record_activity(db, actor, DEACTIVATED, practice_id=None, detail=user.name)
    await db.commit()


async def reactivate_hq_member(db: AsyncSession, actor: Actor, user_id: str) -> None:
    user = await _hq_member(db, user_id)
    if user.status != "blocked":
        return
    user.status = "active" if user.password_hash else "invited"
    record_activity(db, actor, REACTIVATED, practice_id=None, detail=user.name)
    await db.commit()


async def enrol_hq_person(db: AsyncSession, messenger: Messenger, *, name: str, email: str) -> HqEnrolment:
    existing = await account_by_email(db, email, (HQ_REALM,))
    if existing is None:
        return HqEnrolment(await invite_hq_member(db, messenger, None, name=name, email=email), "invited")
    renamed_from = _rename(db, existing, name.strip())
    outcome = ENROLMENT_OUTCOMES[existing.status]
    if existing.status == "invited":
        await resend_hq_invite(db, messenger, None, existing.id)
    await db.commit()
    return HqEnrolment(existing, outcome, renamed_from)


def _rename(db: AsyncSession, user: User, name: str) -> str | None:
    if not name or name == user.name:
        return None
    previous, user.name = user.name, name
    record_activity(db, None, RENAMED, practice_id=None, detail=f"{previous} to {name}")
    return previous


async def _hq_member(db: AsyncSession, user_id: str) -> User:
    user = await db.get(User, user_id)
    if user is None or user.realm != HQ_REALM:
        raise NotFound("member not found")
    return user
