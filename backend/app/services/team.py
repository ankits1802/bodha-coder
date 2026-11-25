from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.messenger import Messenger
from app.core.config import get_settings
from app.core.deps import Actor
from app.core.errors import Conflict, Forbidden, NotFound
from app.core.roles import INVITABLE_ROLES
from app.models import User
from app.services.audit_log import record_activity
from app.services.auth import end_all_sessions, issue_user_token


async def team(db: AsyncSession, actor: Actor) -> list[User]:
    return list((await db.scalars(select(User).where(User.practice_id == actor.practice_id).order_by(User.name))).all())


async def invite(db: AsyncSession, messenger: Messenger, actor: Actor, *, name: str, email: str, role: str) -> User:
    if role not in INVITABLE_ROLES:
        raise Forbidden("that role cannot be invited")
    practice = actor.practice
    seats = await db.scalar(
        select(func.count()).select_from(User).where(User.practice_id == actor.practice_id, User.status != "blocked")
    )
    if practice is None or (seats or 0) >= practice.seats:
        raise Conflict("all seats are in use")
    address = email.strip().lower()
    if await db.scalar(select(User.id).where(User.email == address)):
        raise Conflict("someone already uses that email")
    user = User(practice_id=actor.practice_id, email=address, name=name.strip(), role=role, status="invited")
    db.add(user)
    await db.flush()
    await send_invite(db, messenger, user, practice_name=practice.name)
    record_activity(db, actor, "member invited", practice_id=actor.practice_id, detail=f"{user.name} as {role}")
    await db.commit()
    return user


async def send_invite(db: AsyncSession, messenger: Messenger, user: User, *, practice_name: str) -> None:
    token = await issue_user_token(db, user, "invite")
    link = f"{get_settings().app_url}/set-password#{token}"
    await messenger.email(
        user.email,
        subject=f"Join {practice_name} on Bodha Coder",
        body=f"{user.name}, you have been invited to Bodha Coder. Set your password: {link}",
    )


async def member(db: AsyncSession, actor: Actor, user_id: str) -> User:
    user = await db.get(User, user_id)
    if user is None or user.practice_id != actor.practice_id:
        raise NotFound("member not found")
    return user


async def update_member(
    db: AsyncSession, actor: Actor, user_id: str, *, role: str | None, blocked: bool | None
) -> User:
    user = await member(db, actor, user_id)
    if user.id == actor.user.id:
        raise Forbidden("you can't change your own access")
    if role is not None:
        if role not in INVITABLE_ROLES:
            raise Forbidden("that role cannot be given")
        user.role = role
        await end_all_sessions(db, user)
    if blocked is not None:
        user.status = "blocked" if blocked else ("active" if user.password_hash else "invited")
        await end_all_sessions(db, user)
    record_activity(
        db,
        actor,
        "member updated",
        practice_id=actor.practice_id,
        detail=f"{user.name}: role {user.role}, {user.status}",
    )
    await db.commit()
    return user


async def reset_mfa(db: AsyncSession, actor: Actor, user_id: str) -> None:
    user = await member(db, actor, user_id)
    user.mfa_enabled, user.mfa_secret = False, None
    await end_all_sessions(db, user)
    record_activity(db, actor, "two-step reset", practice_id=actor.practice_id, detail=user.name)
    await db.commit()


async def resend_invite(db: AsyncSession, messenger: Messenger, actor: Actor, user_id: str) -> None:
    user = await member(db, actor, user_id)
    if user.status != "invited" or actor.practice is None:
        raise Conflict("only pending invitations can be resent")
    await send_invite(db, messenger, user, practice_name=actor.practice.name)
    await db.commit()
