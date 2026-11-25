from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import NotFound
from app.core.security import digest
from app.models import Session, User, utcnow


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


async def end_device_session(db: AsyncSession, user: User, session_id: str) -> None:
    session = await db.get(Session, session_id)
    if session is None or session.user_id != user.id or session.revoked_at is not None:
        raise NotFound("that device is not signed in")
    session.revoked_at = utcnow()
    user.token_version += 1
    await db.commit()


async def end_other_sessions(db: AsyncSession, user: User, refresh: str | None) -> None:
    others = update(Session).where(Session.user_id == user.id, Session.revoked_at.is_(None))
    if refresh:
        others = others.where(Session.refresh_hash != digest(refresh))
    await db.execute(others.values(revoked_at=utcnow()))
    user.token_version += 1
    await db.commit()
