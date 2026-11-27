from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import ColumnElement, Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.codes.billing_codes import Code
from app.core.calendar import today_in
from app.models import LANES, VOIDED, Batch, CodeSet, Note, Provider, Suggestion, User, utcnow

PAGE_SIZE = 50
DUE_SOON = timedelta(hours=24)
RECENT_BATCH_DAYS = 3
QUEUE_STATUSES = ("queued", "reading", "ready", "failed")
UNASSIGNED = "none"
ASSIGNED_PATTERN = r"^(me|none|[0-9a-f-]{36})$"
QUEUE_SORTS = ("due", "impact")
DUE_SORT, IMPACT_SORT = QUEUE_SORTS
PROVIDER_LANE = "provider"
PROVIDER_REASONS = ("questions", "waiting_on_provider")
SORT_ORDERS: dict[str, tuple[Any, ...]] = {
    DUE_SORT: (Note.due_at, Note.created_at, Note.id),
    IMPACT_SORT: (func.abs(Note.impact_cents).desc().nulls_last(), Note.due_at, Note.created_at, Note.id),
}


@dataclass(frozen=True)
class QueueFilter:
    lane: str | None = None
    reason: str | None = None
    search: str | None = None
    provider_id: str | None = None
    batch_id: str | None = None
    assigned: str | None = None
    overdue: bool = False
    sort: str = DUE_SORT


async def lane_counts(db: AsyncSession, practice_id: str, *, now: datetime | None = None) -> dict[str, dict[str, int]]:
    return await _ready_counts(db, practice_id, Note.lane, LANES, now=now)


async def provider_reason_counts(
    db: AsyncSession, practice_id: str, *, now: datetime | None = None
) -> dict[str, dict[str, int]]:
    provider_lane = Note.lane == PROVIDER_LANE
    return await _ready_counts(db, practice_id, Note.lane_reason, PROVIDER_REASONS, provider_lane, now=now)


async def _ready_counts(
    db: AsyncSession,
    practice_id: str,
    column: Any,
    keys: Sequence[str],
    *conditions: ColumnElement[bool],
    now: datetime | None,
) -> dict[str, dict[str, int]]:
    soon = (now or utcnow()) + DUE_SOON
    rows = await db.execute(
        select(column, func.count(), func.count().filter(Note.due_at <= soon))
        .where(Note.practice_id == practice_id, Note.status == "ready", *conditions)
        .group_by(column)
    )
    found = {key: {"total": total, "due_soon": due} for key, total, due in rows}
    return {key: found.get(key, {"total": 0, "due_soon": 0}) for key in keys}


def queue_query(practice_id: str, wanted: QueueFilter, *, now: datetime | None = None) -> Select[Any]:
    query = (
        select(Note, Provider.name)
        .join(Provider, Provider.id == Note.provider_id)
        .where(Note.practice_id == practice_id, Note.status.in_(QUEUE_STATUSES), *_conditions(wanted, now or utcnow()))
    )
    return query.order_by(*SORT_ORDERS[wanted.sort])


def _conditions(wanted: QueueFilter, now: datetime) -> list[ColumnElement[bool]]:
    found: list[ColumnElement[bool]] = []
    if wanted.lane or wanted.reason:
        found.append(Note.status == "ready")
    if wanted.lane:
        found.append(Note.lane == wanted.lane)
    if wanted.reason:
        found.append(Note.lane_reason == wanted.reason)
    if wanted.provider_id:
        found.append(Note.provider_id == wanted.provider_id)
    if wanted.batch_id:
        found.append(Note.batch_id == wanted.batch_id)
    if wanted.overdue:
        found.append(Note.due_at < now)
    if wanted.assigned:
        found.append(
            Note.assigned_to.is_(None) if wanted.assigned == UNASSIGNED else Note.assigned_to == wanted.assigned
        )
    if wanted.search:
        pattern = f"%{wanted.search.strip()}%"
        found.append(or_(Note.patient_name.ilike(pattern), Note.file_name.ilike(pattern)))
    return found


async def count_of(db: AsyncSession, query: Select[Any]) -> int:
    return await db.scalar(select(func.count()).select_from(query.order_by(None).subquery())) or 0


async def failed_count(db: AsyncSession, practice_id: str) -> int:
    query = select(Note.id).where(Note.practice_id == practice_id, Note.status == "failed")
    return await count_of(db, query)


async def queue_rows(
    db: AsyncSession, query: Select[Any], *, offset: int, limit: int = PAGE_SIZE
) -> list[dict[str, Any]]:
    rows = (await db.execute(query.offset(offset).limit(limit))).all()
    notes = [note for note, _ in rows]
    billed = await _billed_by_note(db, [note.id for note in notes])
    analysis_ids = [note.current_analysis_id for note in notes if note.current_analysis_id]
    changes = await _changes_by_analysis(db, analysis_ids)
    em_actions = await _em_actions(db, analysis_ids)
    assignees = await user_names(db, {note.assigned_to for note in notes if note.assigned_to})
    return [
        {
            **summary(note, provider_name),
            "assignee_name": assignees.get(note.assigned_to or ""),
            "billed": billed.get(note.id, []),
            "suggested": changes.get(note.current_analysis_id or "", []),
            "em_action": em_actions.get(note.current_analysis_id or ""),
            "impact_cents": note.impact_cents,
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
        "assigned_to": note.assigned_to,
        "payer": note.payer,
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
    return {note_id: [Code.from_json(item).label() for item in codes] for note_id, codes in rows}


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
    return {analysis_id: action for analysis_id, action in rows.all()}


async def today(db: AsyncSession, practice_id: str, zone: ZoneInfo) -> dict[str, Any]:
    lanes = await lane_counts(db, practice_id)
    next_up = await queue_rows(db, queue_query(practice_id, QueueFilter(lane="coder")), offset=0, limit=3)
    since = today_in(zone) - timedelta(days=RECENT_BATCH_DAYS)
    batch_rows = await db.execute(
        select(Batch.id, Provider.name, Batch.service_date, Batch.place_code, Note.status, func.count())
        .join(Provider, Provider.id == Batch.provider_id)
        .join(Note, Note.batch_id == Batch.id)
        .where(Batch.practice_id == practice_id, Batch.service_date >= since, Note.status != VOIDED)
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
        "provider_reasons": await provider_reason_counts(db, practice_id),
        "next_up": next_up,
        "batches": sorted(batches.values(), key=lambda item: item["service_date"], reverse=True),
    }


async def user_names(db: AsyncSession, user_ids: set[str]) -> dict[str, str]:
    if not user_ids:
        return {}
    rows = await db.execute(select(User.id, User.name).where(User.id.in_(user_ids)))
    return {user_id: name for user_id, name in rows.all()}


async def assignee_name(db: AsyncSession, note: Note) -> str | None:
    if note.assigned_to is None:
        return None
    return (await user_names(db, {note.assigned_to})).get(note.assigned_to)


async def compliance_patterns(db: AsyncSession, practice_id: str) -> list[dict[str, Any]]:
    rows = await db.execute(
        select(Provider.name, func.count())
        .join(Note, Note.provider_id == Provider.id)
        .where(Note.practice_id == practice_id, Note.lane == "compliance", Note.status == "ready")
        .group_by(Provider.name)
        .order_by(func.count().desc())
    )
    return [{"provider_name": name, "count": count} for name, count in rows]
