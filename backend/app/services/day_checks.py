from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from itertools import combinations
from typing import Any

from sqlalchemy import ColumnElement, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.calendar import today_in
from app.core.deps import Actor
from app.core.errors import Invalid, NotFound
from app.models import VOIDED, Analysis, Note, NoteText, Provider
from app.services.audit_log import record_access
from app.services.review_actions import note_for
from app.services.visit_levels import is_leveled, is_top_level, visit_codes

__all__ = [
    "CLONED_TEXT",
    "HIGH_LEVEL_SHARE",
    "TIME_OVER_DAY",
    "DayNote",
    "day_flags",
    "day_summary",
    "flagged_days",
    "jaccard",
    "near_duplicates",
    "note_body",
    "note_day",
    "provider_day",
    "shingles",
]

PLAUSIBLE_DAY_MINUTES = 16 * 60
CLONE_SIMILARITY = 0.85
HIGH_LEVEL_LIMIT = 0.60
HIGH_LEVEL_MIN_VISITS = 5
SHINGLE_CHARS = 5
TRIM_LINES = 3
SIMILARITY_DECIMALS = 3
DEFAULT_RANGE_DAYS = 30
MAX_RANGE_DAYS = 92
TIME_OVER_DAY = "time_over_day"
CLONED_TEXT = "cloned_text"
HIGH_LEVEL_SHARE = "high_level_share"


@dataclass(frozen=True)
class DayNote:
    id: str
    patient_name: str | None
    status: str
    lane: str | None
    em_code: str | None
    minutes: int | None


def note_body(text: str) -> str:
    lines = [line for line in text.splitlines() if line.strip()]
    kept = lines[TRIM_LINES:-TRIM_LINES] if len(lines) > 2 * TRIM_LINES else []
    return " ".join(" ".join(kept).split()).casefold()


def shingles(text: str) -> frozenset[str]:
    return frozenset(text[start : start + SHINGLE_CHARS] for start in range(len(text) - SHINGLE_CHARS + 1))


def jaccard(first: frozenset[str], second: frozenset[str]) -> float:
    union = first | second
    return len(first & second) / len(union) if union else 0.0


def near_duplicates(texts: Mapping[str, str]) -> tuple[int, list[dict[str, Any]]]:
    sets = {note_id: found for note_id, text in texts.items() if (found := shingles(note_body(text)))}
    pairs = []
    for (first, first_set), (second, second_set) in combinations(sets.items(), 2):
        similarity = jaccard(first_set, second_set)
        if similarity >= CLONE_SIMILARITY:
            pairs.append({"first": first, "second": second, "similarity": round(similarity, SIMILARITY_DECIMALS)})
    return len(sets), pairs


def day_flags(total_minutes: int, share: float | None, visits: int, duplicates: int) -> list[str]:
    flags = []
    if total_minutes > PLAUSIBLE_DAY_MINUTES:
        flags.append(TIME_OVER_DAY)
    if duplicates:
        flags.append(CLONED_TEXT)
    if share is not None and visits >= HIGH_LEVEL_MIN_VISITS and share > HIGH_LEVEL_LIMIT:
        flags.append(HIGH_LEVEL_SHARE)
    return flags


def day_summary(notes: Sequence[DayNote], texts: Mapping[str, str]) -> dict[str, Any]:
    timed = [note.minutes for note in notes if note.minutes is not None]
    leveled = [note.em_code for note in notes if note.em_code and is_leveled(note.em_code)]
    top = sum(1 for code in leveled if is_top_level(code))
    share = top / len(leveled) if leveled else None
    counts: dict[str, int] = {}
    for note in notes:
        if note.em_code:
            counts[note.em_code] = counts.get(note.em_code, 0) + 1
    compared, duplicates = near_duplicates(texts)
    return {
        "notes": [asdict(note) for note in notes],
        "total_minutes": sum(timed),
        "timed_notes": len(timed),
        "visits": len(leveled),
        "levels": [{"code": code, "count": count} for code, count in sorted(counts.items())],
        "high_level_visits": top,
        "high_level_share": share,
        "compared": compared,
        "duplicates": duplicates,
        "flags": day_flags(sum(timed), share, len(leveled), len(duplicates)),
    }


async def provider_day(db: AsyncSession, practice_id: str, provider_id: str, service_date: date) -> dict[str, Any]:
    provider = await db.get(Provider, provider_id)
    if provider is None or provider.practice_id != practice_id:
        raise NotFound("provider not found")
    rows = await _day_rows(db, practice_id, Note.provider_id == provider_id, Note.service_date == service_date)
    notes = await _day_notes(db, rows)
    texts = await _document_texts(db, [note.id for note in notes])
    return {
        "provider": {"id": provider.id, "name": provider.name},
        "service_date": service_date.isoformat(),
        **day_summary(notes, texts),
    }


async def note_day(db: AsyncSession, actor: Actor, note_id: str) -> dict[str, Any]:
    note = await note_for(db, actor, note_id)
    day = await provider_day(db, actor.practice_id, note.provider_id, note.service_date)
    record_access(db, actor, "opened provider day", note_id=note.id, detail=f"{len(day['notes'])} notes")
    await db.commit()
    return {"note_id": note.id, **day}


async def flagged_days(db: AsyncSession, actor: Actor, start: date | None, end: date | None) -> dict[str, Any]:
    start, end = _range(start, end, today_in(actor.zone))
    rows = await _day_rows(db, actor.practice_id, Note.service_date >= start, Note.service_date <= end)
    groups: dict[tuple[str, date], list[tuple[Any, ...]]] = {}
    for row in rows:
        groups.setdefault((row.provider_id, row.service_date), []).append(row)
    names = dict(
        (await db.execute(select(Provider.id, Provider.name).where(Provider.practice_id == actor.practice_id))).all()
    )
    days = []
    for (provider_id, service_date), members in groups.items():
        notes = await _day_notes(db, members)
        summary = day_summary(notes, await _document_texts(db, [note.id for note in notes]))
        if summary["flags"]:
            provider = {"id": provider_id, "name": names.get(provider_id, "")}
            days.append({"provider": provider, "service_date": service_date.isoformat(), **summary})
    record_access(db, actor, "listed provider days", detail=f"{len(days)} flagged days from {start} to {end}")
    await db.commit()
    days.sort(key=lambda day: (day["service_date"], day["provider"]["name"]), reverse=True)
    return {"from": start.isoformat(), "to": end.isoformat(), "days": days}


def _range(start: date | None, end: date | None, today: date) -> tuple[date, date]:
    last = end or today
    first = start or last - timedelta(days=DEFAULT_RANGE_DAYS - 1)
    if first > last:
        raise Invalid("the start date is after the end date")
    if (last - first).days + 1 > MAX_RANGE_DAYS:
        raise Invalid(f"choose at most {MAX_RANGE_DAYS} days")
    return first, last


async def _day_rows(db: AsyncSession, practice_id: str, *conditions: ColumnElement[bool]) -> list[Any]:
    query = (
        select(
            Note.id,
            Note.provider_id,
            Note.service_date,
            Note.patient_name,
            Note.status,
            Note.lane,
            Analysis.report["em"].label("em"),
        )
        .outerjoin(Analysis, Analysis.id == Note.current_analysis_id)
        .where(Note.practice_id == practice_id, Note.status != VOIDED, *conditions)
        .order_by(Note.service_date, Note.created_at, Note.id)
    )
    return list((await db.execute(query)).all())


async def _day_notes(db: AsyncSession, rows: Sequence[Any]) -> list[DayNote]:
    codes = await visit_codes(db, [row.id for row in rows])
    return [
        DayNote(row.id, row.patient_name, row.status, row.lane, codes.get(row.id), _minutes(row.em)) for row in rows
    ]


def _minutes(em: Any) -> int | None:
    value = em.get("time_minutes") if isinstance(em, dict) else None
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


async def _document_texts(db: AsyncSession, note_ids: list[str]) -> dict[str, str]:
    if len(note_ids) < 2:
        return {}
    rows = await db.execute(
        select(NoteText.note_id, NoteText.text)
        .where(NoteText.note_id.in_(note_ids), NoteText.source == "document")
        .order_by(NoteText.note_id, NoteText.revision.desc())
        .distinct(NoteText.note_id)
    )
    found = dict(rows.all())
    return {note_id: found[note_id] for note_id in note_ids if found.get(note_id)}
