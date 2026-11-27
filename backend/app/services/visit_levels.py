from __future__ import annotations

from collections.abc import Iterable, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.codes.billing_codes import Code
from app.codes.em import em_position, is_em_code
from app.models import Note
from app.services.code_sets import latest_codes_for
from app.services.placement import SETTLED_STATUSES

__all__ = ["is_leveled", "is_top_level", "visit_code", "visit_codes"]

TOP_LEVELS = 2
MIN_LEVELS = 3


def visit_code(codes: Iterable[Code]) -> str | None:
    return next((code.code for code in codes if code.type == "CPT" and is_em_code(code.code)), None)


def is_leveled(code: str) -> bool:
    position = em_position(code)
    return position is not None and len(position[0].levels) >= MIN_LEVELS


def is_top_level(code: str) -> bool:
    position = em_position(code)
    if position is None or not is_leveled(code):
        return False
    family, index = position
    return index >= len(family.levels) - TOP_LEVELS


async def visit_codes(db: AsyncSession, note_ids: Sequence[str]) -> dict[str, str]:
    if not note_ids:
        return {}
    statuses = dict((await db.execute(select(Note.id, Note.status).where(Note.id.in_(note_ids)))).all())
    settled = [note_id for note_id in note_ids if statuses.get(note_id) in SETTLED_STATUSES]
    final, billed = await latest_codes_for(db, "final", settled), await latest_codes_for(db, "billed", note_ids)
    found: dict[str, str] = {}
    for note_id in note_ids:
        codes = final.get(note_id)
        code = visit_code(codes if codes is not None else billed.get(note_id, ()))
        if code is not None:
            found[note_id] = code
    return found
