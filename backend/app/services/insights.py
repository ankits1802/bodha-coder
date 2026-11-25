from __future__ import annotations

from datetime import timedelta
from typing import Any

from sqlalchemy import Date, cast, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Analysis, Note, Provider, Suggestion, utcnow

OUTCOME_BY_ACTION = {
    ("em", "keep"): "matched",
    ("em", "raise"): "billed_too_low",
    ("em", "lower"): "billed_too_high",
    ("diagnosis", "replace"): "diagnosis_changes",
    ("diagnosis", "add"): "diagnosis_changes",
    ("diagnosis", "remove"): "diagnosis_changes",
}


async def insights(db: AsyncSession, practice_id: str, *, days: int, time_zone: str) -> dict[str, Any]:
    since = utcnow() - timedelta(days=days)
    first_runs = (
        select(Analysis)
        .join(Note, Note.id == Analysis.note_id)
        .where(Note.practice_id == practice_id, Analysis.revision == 1, Analysis.finished_at >= since)
        .subquery()
    )
    local_day = cast(func.timezone(time_zone, first_runs.c.finished_at), Date)
    per_day = await db.execute(select(local_day, func.count()).group_by(text("1")).order_by(text("1")))
    timing = (
        await db.execute(
            select(func.count(), func.count().filter(Note.approved_at <= Note.due_at)).where(
                Note.practice_id == practice_id, Note.approved_at >= since
            )
        )
    ).one()
    outcomes = await _outcomes(db, practice_id, since)
    return {
        "days": days,
        "per_day": [{"date": day.isoformat(), "notes": count} for day, count in per_day],
        "approved": timing[0],
        "approved_on_time": timing[1],
        "outcomes": outcomes,
        "providers": await _providers(db, practice_id, since),
    }


async def _outcomes(db: AsyncSession, practice_id: str, since: Any) -> dict[str, int]:
    rows = await db.execute(
        select(Suggestion.kind, Suggestion.action, func.count())
        .join(Note, Note.current_analysis_id == Suggestion.analysis_id)
        .where(Note.practice_id == practice_id, Note.created_at >= since, Suggestion.kind.in_(("em", "diagnosis")))
        .group_by(Suggestion.kind, Suggestion.action)
    )
    counts = dict.fromkeys(OUTCOME_BY_ACTION.values(), 0)
    for kind, action, count in rows:
        bucket = OUTCOME_BY_ACTION.get((kind, action))
        if bucket:
            counts[bucket] += count
    return counts


async def _providers(db: AsyncSession, practice_id: str, since: Any) -> list[dict[str, Any]]:
    rows = await db.execute(
        select(Provider.name, func.count(Note.id), func.count(Note.id).filter(Suggestion.action == "keep"))
        .join(Note, Note.provider_id == Provider.id)
        .join(Suggestion, (Suggestion.analysis_id == Note.current_analysis_id) & (Suggestion.kind == "em"))
        .where(Note.practice_id == practice_id, Note.created_at >= since)
        .group_by(Provider.name)
        .order_by(func.count(Note.id).desc())
        .limit(20)
    )
    return [{"provider_name": name, "notes": total, "matched": matched} for name, total, matched in rows]
