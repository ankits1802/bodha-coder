from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.codes.mips_catalog import ADDABLE_MEASURE_IDS, VERIFIED_MIPS_MEASURES, addable_measure
from app.codes.mips_scope import MipsScope, practice_keys, practice_scope, validate_measure_ids
from app.core.deps import Actor
from app.core.errors import Conflict, Invalid
from app.models import MipsList
from app.services.audit_log import record_activity
from app.services.practice_measures import definitions_for, live_measures, measure_view

__all__ = ["mips_overview", "practice_mips_scope", "save_mips"]


async def mips_overview(db: AsyncSession, practice_id: str) -> dict[str, Any]:
    stored = await db.scalar(select(MipsList.measure_ids).where(MipsList.practice_id == practice_id))
    addable = [
        {"id": mid, "title": (addable_measure(mid) or {}).get("title", "")} for mid in sorted(ADDABLE_MEASURE_IDS)
    ]
    return {
        "standard": [{"id": mid, "title": title} for mid, (title, _spec) in VERIFIED_MIPS_MEASURES.items()],
        "addable": addable,
        "practice": [measure_view(row) for row in await live_measures(db, practice_id)],
        "measure_ids": stored or [],
        "uses_standard": not stored,
    }


async def practice_mips_scope(db: AsyncSession, practice_id: str) -> MipsScope | None:
    stored = await db.scalar(select(MipsList.measure_ids).where(MipsList.practice_id == practice_id))
    return practice_scope(stored, await definitions_for(db, practice_id, practice_keys(stored)))


async def save_mips(db: AsyncSession, actor: Actor, *, measure_ids: list[str], expected: list[str]) -> list[str]:
    row = await db.scalar(select(MipsList).where(MipsList.practice_id == actor.practice_id).with_for_update())
    if (row.measure_ids if row else []) != expected:
        raise Conflict("someone else changed this list; reload and try again")
    chosen = await _chosen(db, actor.practice_id, measure_ids)
    if not chosen and row is not None:
        await db.delete(row)
    elif row is None and chosen:
        db.add(MipsList(practice_id=actor.practice_id, measure_ids=chosen, updated_by=actor.user.id))
    elif row is not None:
        row.measure_ids, row.updated_by = chosen, actor.user.id
    record_activity(
        db, actor, "MIPS list changed", practice_id=actor.practice_id, detail=", ".join(chosen) or "standard list"
    )
    await db.commit()
    return chosen


async def _chosen(db: AsyncSession, practice_id: str, measure_ids: list[str]) -> list[str]:
    keys = practice_keys(measure_ids)
    defined = await definitions_for(db, practice_id, keys)
    missing = [key for key in keys if key not in defined]
    if missing:
        raise Invalid(f"practice measure {missing[0]} is retired or does not exist; reload and choose again")
    try:
        cms = validate_measure_ids([item for item in measure_ids if item not in keys])
    except ValueError as error:
        raise Invalid(str(error)) from error
    return cms + list(keys)
