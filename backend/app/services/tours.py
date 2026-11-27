from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import Forbidden
from app.models import PersonTour, User, utcnow

__all__ = ["record_tour", "tours_taken"]


async def tours_taken(db: AsyncSession, user: User) -> list[dict[str, Any]]:
    rows = await db.scalars(_records_of(user).order_by(PersonTour.version))
    return [_view(row) for row in rows]


async def record_tour(db: AsyncSession, user: User, tour: str, *, version: int, outcome: str) -> dict[str, Any]:
    if tour != user.realm:
        raise Forbidden("this tour is not for this account")
    values = {"user_id": user.id, "tour": tour, "version": version, f"{outcome}_at": utcnow()}
    await db.execute(insert(PersonTour).values(**values).on_conflict_do_nothing())
    await db.commit()
    row = (await db.scalars(_records_of(user).where(PersonTour.version == version))).one()
    return _view(row)


def _records_of(user: User):
    return select(PersonTour).where(PersonTour.user_id == user.id, PersonTour.tour == user.realm)


def _view(row: PersonTour) -> dict[str, Any]:
    return {
        "tour": row.tour,
        "version": row.version,
        "completed_at": _iso(row.completed_at),
        "skipped_at": _iso(row.skipped_at),
    }


def _iso(moment: datetime | None) -> str | None:
    return moment.isoformat() if moment else None
