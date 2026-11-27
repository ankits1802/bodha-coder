from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.codes.billing_codes import Code
from app.models import CodeSet

__all__ = ["latest_codes", "next_revision"]


async def next_revision(db: AsyncSession, model: type[Any], note_id: str, **filters: str) -> int:
    query = select(func.max(model.revision)).where(model.note_id == note_id)
    for column, value in filters.items():
        query = query.where(getattr(model, column) == value)
    return ((await db.scalar(query)) or 0) + 1


async def latest_codes(db: AsyncSession, note_id: str, kind: str) -> tuple[Code, ...]:
    row = await db.scalar(
        select(CodeSet)
        .where(CodeSet.note_id == note_id, CodeSet.kind == kind)
        .order_by(CodeSet.revision.desc())
        .limit(1)
    )
    return tuple(Code.from_json(item) for item in (row.codes if row else []))
