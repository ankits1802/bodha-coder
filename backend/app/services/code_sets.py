from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.codes.billing_codes import Code
from app.models import CodeSet

__all__ = ["latest_codes", "latest_codes_for", "next_revision", "original_codes"]


async def next_revision(db: AsyncSession, model: type[Any], note_id: str, **filters: str) -> int:
    query = select(func.max(model.revision)).where(model.note_id == note_id)
    for column, value in filters.items():
        query = query.where(getattr(model, column) == value)
    return ((await db.scalar(query)) or 0) + 1


async def latest_codes(db: AsyncSession, note_id: str, kind: str) -> tuple[Code, ...]:
    return await _codes_at(db, note_id, kind, CodeSet.revision.desc())


async def original_codes(db: AsyncSession, note_id: str, kind: str) -> tuple[Code, ...]:
    return await _codes_at(db, note_id, kind, CodeSet.revision)


async def latest_codes_for(db: AsyncSession, kind: str, note_ids: Sequence[str]) -> dict[str, tuple[Code, ...]]:
    if not note_ids:
        return {}
    rows = await db.execute(
        select(CodeSet.note_id, CodeSet.codes)
        .where(CodeSet.kind == kind, CodeSet.note_id.in_(note_ids))
        .order_by(CodeSet.note_id, CodeSet.revision.desc())
        .distinct(CodeSet.note_id)
    )
    return {note_id: tuple(Code.from_json(item) for item in codes) for note_id, codes in rows}


async def _codes_at(db: AsyncSession, note_id: str, kind: str, order: Any) -> tuple[Code, ...]:
    row = await db.scalar(
        select(CodeSet).where(CodeSet.note_id == note_id, CodeSet.kind == kind).order_by(order).limit(1)
    )
    return tuple(Code.from_json(item) for item in (row.codes if row else []))
