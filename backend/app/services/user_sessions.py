from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.deps import Client
from app.core.errors import NotFound
from app.core.security import digest
from app.models import Session, User, utcnow
from app.services.auth_events import AuthEventFacts, record_auth_event

__all__ = [
    "SESSION_REVOKED",
    "SignedInDevice",
    "end_all_sessions",
    "end_device_session",
    "end_other_sessions",
    "end_practice_sessions",
    "signed_in_devices",
]

SESSION_REVOKED = "session_revoked"
ONE_DEVICE = "one device"
OTHER_DEVICES = "other devices"


@dataclass(frozen=True)
class SignedInDevice:
    session: Session
    current: bool


async def signed_in_devices(db: AsyncSession, user: User, refresh: str | None) -> list[SignedInDevice]:
    now = utcnow()
    idle_since = now - timedelta(minutes=get_settings().session_idle_minutes)
    rows = await db.scalars(
        select(Session)
        .where(
            Session.user_id == user.id,
            Session.revoked_at.is_(None),
            Session.expires_at > now,
            Session.last_used_at > idle_since,
        )
        .order_by(Session.last_used_at.desc())
    )
    current = digest(refresh) if refresh else None
    return [SignedInDevice(row, row.refresh_hash == current) for row in rows]


async def end_device_session(db: AsyncSession, user: User, session_id: str, *, client: Client) -> None:
    session = await db.get(Session, session_id)
    if session is None or session.user_id != user.id or session.revoked_at is not None:
        raise NotFound("that device is not signed in")
    session.revoked_at = utcnow()
    user.token_version += 1
    await record_auth_event(db, SESSION_REVOKED, user, AuthEventFacts(client, detail=ONE_DEVICE))
    await db.commit()


async def end_other_sessions(db: AsyncSession, user: User, refresh: str | None, *, client: Client) -> None:
    others = update(Session).where(Session.user_id == user.id, Session.revoked_at.is_(None))
    if refresh:
        others = others.where(Session.refresh_hash != digest(refresh))
    ended = await db.execute(others.values(revoked_at=utcnow()))
    user.token_version += 1
    if ended.rowcount:
        await record_auth_event(db, SESSION_REVOKED, user, AuthEventFacts(client, detail=OTHER_DEVICES))
    await db.commit()


async def end_all_sessions(db: AsyncSession, user: User, *, reason: str, client: Client) -> None:
    user.token_version += 1
    ended = await db.execute(
        update(Session).where(Session.user_id == user.id, Session.revoked_at.is_(None)).values(revoked_at=utcnow())
    )
    if ended.rowcount:
        await record_auth_event(db, SESSION_REVOKED, user, AuthEventFacts(client, detail=reason))


async def end_practice_sessions(db: AsyncSession, user: User, practice_id: str, *, reason: str, client: Client) -> None:
    ended = await db.execute(
        update(Session)
        .where(Session.user_id == user.id, Session.practice_id == practice_id, Session.revoked_at.is_(None))
        .values(revoked_at=utcnow())
    )
    if ended.rowcount:
        facts = AuthEventFacts(client, practice_id=practice_id, detail=reason)
        await record_auth_event(db, SESSION_REVOKED, user, facts)
