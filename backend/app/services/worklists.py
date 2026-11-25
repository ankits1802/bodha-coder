from __future__ import annotations

from datetime import timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.calendar import today_in
from app.models import LANES, Batch, CodeSet, Note, Provider, Suggestion, User, utcnow

PAGE_SIZE = 50
DUE_SOON = timedelta(hours=24)
RECENT_BATCH_DAYS = 3


async def lane_counts(db: AsyncSession, practice_id: str) -> dict[str, dict[str, int]]:
    soon = utcnow() + DUE_SOON
    rows = await db.execute(
        select(Note.lane, func.count(), func.count().filter(Note.due_at <= soon))
        .where(Note.practice_id == practice_id, Note.status == "ready")
        .group_by(Note.lane)
    )
    found = {lane: {"total": total, "due_soon": due} for lane, total, due in rows}
    return {lane: found.get(lane, {"total": 0, "due_soon": 0}) for lane in LANES}


def queue_query(practice_id: str, *, lane: str | None, search: str | None, provider_id: str | None) -> Select[Any]:
    query = (
        select(Note, Provider.name)
        .join(Provider, Provider.id == Note.provider_id)
        .where(Note.practice_id == practice_id, Note.status.in_(("queued", "reading", "ready", "failed")))
    )
    if lane:
        query = query.where(Note.lane == lane, Note.status == "ready")
    if provider_id:
        query = query.where(Note.provider_id == provider_id)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(or_(Note.patient_name.ilike(pattern), Note.file_name.ilike(pattern)))
    return query.order_by(Note.due_at, Note.created_at)


async def queue_rows(
    db: AsyncSession, query: Select[Any], *, offset: int, limit: int = PAGE_SIZE
) -> list[dict[str, Any]]:
    rows = (await db.execute(query.offset(offset).limit(limit))).all()
    notes = [note for note, _ in rows]
    billed = await _billed_by_note(db, [note.id for note in notes])
    analysis_ids = [note.current_analysis_id for note in notes if note.current_analysis_id]
    changes = await _changes_by_analysis(db, analysis_ids)
    em_actions = await _em_actions(db, analysis_ids)
    return [
        {
            **summary(note, provider_name),
            "billed": billed.get(note.id, []),
            "suggested": changes.get(note.current_analysis_id or "", []),
            "em_action": em_actions.get(note.current_analysis_id or ""),
        }
        for note, provider_name in rows
    ]


def summary(note: Note, provider_name: str) -> dict[str, Any]:
    return {
        "id": note.id,
        "patient_name": note.patient_name,
        "provider_name": provider_name,
        "service_date": note.service_date.isoformat(),
        "status": note.status,
        "lane": note.lane,
        "lane_reason": note.lane_reason,
        "headline": note.headline,
        "place_code": note.place_code,
        "visit_type": note.visit_type,
        "flag_reason": note.flag_reason,
        "flagged_by": note.flagged_by,
        "due_at": note.due_at.isoformat(),
        "file_name": note.file_name,
    }


async def _billed_by_note(db: AsyncSession, note_ids: list[str]) -> dict[str, list[str]]:
    if not note_ids:
        return {}
    latest = (
        select(CodeSet.note_id, func.max(CodeSet.revision).label("revision"))
        .where(CodeSet.note_id.in_(note_ids), CodeSet.kind == "billed")
        .group_by(CodeSet.note_id)
        .subquery()
    )
    rows = await db.execute(
        select(CodeSet.note_id, CodeSet.codes)
        .join(latest, and_(CodeSet.note_id == latest.c.note_id, CodeSet.revision == latest.c.revision))
        .where(CodeSet.kind == "billed")
    )
    return {note_id: [item["code"] for item in codes] for note_id, codes in rows}


async def _changes_by_analysis(db: AsyncSession, analysis_ids: list[str]) -> dict[str, list[str]]:
    if not analysis_ids:
        return {}
    rows = await db.execute(
        select(Suggestion.analysis_id, Suggestion.code_after)
        .where(
            Suggestion.analysis_id.in_(analysis_ids),
            Suggestion.code_after.is_not(None),
            Suggestion.action.in_(("lower", "raise", "replace", "add")),
        )
        .order_by(Suggestion.kind)
    )
    found: dict[str, list[str]] = {}
    for analysis_id, code in rows:
        found.setdefault(analysis_id, []).append(code)
    return found


async def _em_actions(db: AsyncSession, analysis_ids: list[str]) -> dict[str, str]:
    if not analysis_ids:
        return {}
    rows = await db.execute(
        select(Suggestion.analysis_id, Suggestion.action).where(
            Suggestion.analysis_id.in_(analysis_ids), Suggestion.kind == "em"
        )
    )
    return dict(rows.tuples().all())


async def today(db: AsyncSession, practice_id: str, zone: ZoneInfo) -> dict[str, Any]:
    lanes = await lane_counts(db, practice_id)
    next_up = await queue_rows(
        db, queue_query(practice_id, lane="coder", search=None, provider_id=None), offset=0, limit=3
    )
    since = today_in(zone) - timedelta(days=RECENT_BATCH_DAYS)
    batch_rows = await db.execute(
        select(Batch.id, Provider.name, Batch.service_date, Batch.place_code, Note.status, func.count())
        .join(Provider, Provider.id == Batch.provider_id)
        .join(Note, Note.batch_id == Batch.id)
        .where(Batch.practice_id == practice_id, Batch.service_date >= since)
        .group_by(Batch.id, Provider.name, Batch.service_date, Batch.place_code, Note.status)
    )
    batches: dict[str, dict[str, Any]] = {}
    for batch_id, provider, service_date, place, status, count in batch_rows:
        entry = batches.setdefault(
            batch_id,
            {
                "id": batch_id,
                "provider_name": provider,
                "service_date": service_date.isoformat(),
                "place_code": place,
                "counts": {},
            },
        )
        entry["counts"][status] = count
    waiting = sum(item["total"] for item in lanes.values())
    due_soon = sum(item["due_soon"] for item in lanes.values())
    return {
        "waiting": waiting,
        "due_soon": due_soon,
        "lanes": lanes,
        "next_up": next_up,
        "batches": sorted(batches.values(), key=lambda item: item["service_date"], reverse=True),
    }


async def user_names(db: AsyncSession, user_ids: set[str]) -> dict[str, str]:
    if not user_ids:
        return {}
    return dict((await db.execute(select(User.id, User.name).where(User.id.in_(user_ids)))).tuples().all())


async def compliance_patterns(db: AsyncSession, practice_id: str) -> list[dict[str, Any]]:
    rows = await db.execute(
        select(Provider.name, func.count())
        .join(Note, Note.provider_id == Provider.id)
        .where(Note.practice_id == practice_id, Note.lane == "compliance", Note.status == "ready")
        .group_by(Provider.name)
        .order_by(func.count().desc())
    )
    return [{"provider_name": name, "count": count} for name, count in rows]
