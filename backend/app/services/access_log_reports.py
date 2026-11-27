from __future__ import annotations

import csv
import io
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.calendar import day_bounds, today_in
from app.core.deps import Actor
from app.core.errors import Invalid
from app.models import AccessLog, Note
from app.services.audit_log import record_access
from app.services.billing import safe_cell
from app.services.worklists import count_of

__all__ = [
    "ACCESS_LOG_PAGE",
    "EXPORT_COLUMNS",
    "EXPORT_LIMIT",
    "AccessLogFilter",
    "access_log_csv",
    "access_log_page",
    "csv_values",
    "filter_summary",
    "write_csv",
]

ACCESS_LOG_PAGE = 200
EXPORT_LIMIT = 100_000
VIEWED, EXPORTED = "viewed access log", "exported access log"
LIKE_ESCAPE = "\\"
LIKE_MARKS = ("%", "_", LIKE_ESCAPE)
EXPORT_COLUMNS = (
    "at",
    "actor",
    "actor_kind",
    "action",
    "note_id",
    "detail",
    "ip",
    "user_agent",
    "chain_seq",
    "prev_hash",
    "row_hash",
)


@dataclass(frozen=True)
class AccessLogFilter:
    start: date | None = None
    end: date | None = None
    user_id: str | None = None
    action: str | None = None
    note_id: str | None = None
    patient: str | None = None
    birth_date: date | None = None


async def access_log_page(db: AsyncSession, actor: Actor, chosen: AccessLogFilter, *, offset: int) -> dict[str, Any]:
    query = _query(actor, chosen)
    rows = await db.scalars(
        query.order_by(AccessLog.created_at.desc(), AccessLog.id).offset(offset).limit(ACCESS_LOG_PAGE)
    )
    page = {
        "items": [_entry(row) for row in rows],
        "total": await count_of(db, query),
        "offset": offset,
        "page_size": ACCESS_LOG_PAGE,
        "actions": await _actions(db, actor, chosen),
        "people": await _people(db, actor, chosen),
    }
    record_access(db, actor, VIEWED, detail=filter_summary(actor, chosen))
    await db.commit()
    return page


async def access_log_csv(db: AsyncSession, actor: Actor, chosen: AccessLogFilter) -> str:
    query = _query(actor, chosen)
    total = await count_of(db, query)
    if total > EXPORT_LIMIT:
        raise Invalid(f"{total} entries match; narrow the dates or filters to at most {EXPORT_LIMIT}")
    rows = await db.scalars(query.order_by(AccessLog.created_at, AccessLog.chain_seq))
    content = write_csv(rows)
    record_access(db, actor, EXPORTED, detail=f"{total} entries; {filter_summary(actor, chosen)}")
    await db.commit()
    return content


def write_csv(rows: Iterable[AccessLog]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(EXPORT_COLUMNS)
    for row in rows:
        writer.writerow([safe_cell(value) for value in csv_values(row)])
    return buffer.getvalue()


def filter_summary(actor: Actor, chosen: AccessLogFilter) -> str:
    start, end = _days(actor, chosen)
    named = {
        "person": chosen.user_id,
        "action": chosen.action,
        "note": chosen.note_id,
        "patient": chosen.patient or chosen.birth_date,
    }
    used = [name for name, value in named.items() if value]
    return f"{start.isoformat()} to {end.isoformat()}" + (f"; by {', '.join(used)}" if used else "")


def _days(actor: Actor, chosen: AccessLogFilter) -> tuple[date, date]:
    today = today_in(actor.zone)
    start, end = chosen.start or chosen.end or today, chosen.end or chosen.start or today
    if start > end:
        raise Invalid("the start date is after the end date")
    return start, end


def _in_range(actor: Actor, chosen: AccessLogFilter) -> tuple[Any, ...]:
    first, last = _days(actor, chosen)
    return (
        AccessLog.practice_id == actor.practice_id,
        AccessLog.created_at >= day_bounds(first, actor.zone)[0],
        AccessLog.created_at < day_bounds(last, actor.zone)[1],
    )


def _query(actor: Actor, chosen: AccessLogFilter) -> Select[Any]:
    query = select(AccessLog).where(*_in_range(actor, chosen))
    if chosen.user_id:
        query = query.where(AccessLog.actor_id == chosen.user_id)
    if chosen.action:
        query = query.where(AccessLog.action == chosen.action)
    if chosen.note_id:
        query = query.where(AccessLog.note_id == chosen.note_id)
    if chosen.patient or chosen.birth_date:
        query = query.where(AccessLog.note_id.in_(_patient_notes(actor.practice_id, chosen)))
    return query


def _patient_notes(practice_id: str, chosen: AccessLogFilter) -> Select[Any]:
    notes = select(Note.id).where(Note.practice_id == practice_id)
    if chosen.patient:
        notes = notes.where(Note.patient_name.ilike(_containing(chosen.patient), escape=LIKE_ESCAPE))
    if chosen.birth_date:
        notes = notes.where(Note.patient_birth_date == chosen.birth_date)
    return notes


def _containing(text: str) -> str:
    escaped = "".join(LIKE_ESCAPE + mark if mark in LIKE_MARKS else mark for mark in text.strip())
    return f"%{escaped}%"


async def _people(db: AsyncSession, actor: Actor, chosen: AccessLogFilter) -> list[dict[str, str]]:
    query = select(AccessLog.actor_id, AccessLog.actor_name).where(*_in_range(actor, chosen)).distinct()
    rows = (await db.execute(query.order_by(AccessLog.actor_name, AccessLog.actor_id))).all()
    return [{"id": actor_id, "name": name} for actor_id, name in rows]


async def _actions(db: AsyncSession, actor: Actor, chosen: AccessLogFilter) -> list[str]:
    query = select(AccessLog.action).where(*_in_range(actor, chosen)).distinct().order_by(AccessLog.action)
    return list((await db.scalars(query)).all())


def _entry(row: AccessLog) -> dict[str, Any]:
    return {
        "at": row.created_at.isoformat(),
        "actor": row.actor_name,
        "actor_kind": row.actor_kind,
        "action": row.action,
        "note_id": row.note_id,
        "detail": row.detail,
        "ip": row.ip,
        "user_agent": row.user_agent,
    }


def csv_values(row: AccessLog) -> list[object]:
    return [
        row.created_at.isoformat(),
        row.actor_name,
        row.actor_kind,
        row.action,
        row.note_id,
        row.detail,
        row.ip,
        row.user_agent,
        row.chain_seq,
        row.prev_hash,
        row.row_hash,
    ]
