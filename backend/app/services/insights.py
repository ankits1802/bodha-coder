from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from statistics import median
from typing import Any

from sqlalchemy import Date, cast, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.codes.billing_codes import Code, claim_changes
from app.models import Analysis, CodeSet, Note, Provider, Suggestion, User, utcnow
from app.services.estimates import estimate_difference, money
from app.services.placement import SETTLED_STATUSES

__all__ = ["ApprovedNote", "coder_productivity", "estimated_differences", "insights"]

OUTCOME_BY_ACTION = {
    ("em", "keep"): "matched",
    ("em", "raise"): "billed_too_low",
    ("em", "lower"): "billed_too_high",
    ("diagnosis", "replace"): "diagnosis_changes",
    ("diagnosis", "add"): "diagnosis_changes",
    ("diagnosis", "remove"): "diagnosis_changes",
}
MINUTE_DECIMALS = 1


@dataclass(frozen=True)
class ApprovedNote:
    note_id: str
    provider_name: str
    approver_id: str
    approver_name: str
    place_code: str
    service_date: date
    ready_at: datetime | None
    approved_at: datetime
    final: tuple[Code, ...]
    billed: tuple[Code, ...]


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
    approved = await _approved_notes(db, practice_id, since)
    return {
        "days": days,
        "per_day": [{"date": day.isoformat(), "notes": count} for day, count in per_day],
        "approved": timing[0],
        "approved_on_time": timing[1],
        "outcomes": outcomes,
        "providers": await _providers(db, practice_id, since),
        "estimates": estimated_differences(approved),
        "people": coder_productivity(approved),
    }


def estimated_differences(notes: Iterable[ApprovedNote]) -> dict[str, Any]:
    by_provider: dict[str, list[Decimal]] = {}
    for item in notes:
        difference = estimate_difference(item.final, item.billed, item.place_code, item.service_date)
        if difference is not None:
            by_provider.setdefault(item.provider_name, []).append(difference)
    providers = [
        {"provider_name": name, "notes": len(values), "difference": money(sum(values, Decimal("0.00")))}
        for name, values in by_provider.items()
    ]
    every = [value for values in by_provider.values() for value in values]
    return {
        "notes": len(every),
        "difference": money(sum(every, Decimal("0.00"))),
        "providers": sorted(providers, key=lambda row: (-row["notes"], row["provider_name"])),
    }


def coder_productivity(notes: Iterable[ApprovedNote]) -> list[dict[str, Any]]:
    by_person: dict[str, list[ApprovedNote]] = {}
    for item in notes:
        by_person.setdefault(item.approver_id, []).append(item)
    people = [_person(items) for items in by_person.values()]
    return sorted(people, key=lambda row: (-row["approved"], row["name"]))


def _person(items: list[ApprovedNote]) -> dict[str, Any]:
    waits = [minutes for item in items if (minutes := _minutes_to_approve(item)) is not None]
    return {
        "id": items[0].approver_id,
        "name": items[0].approver_name,
        "approved": len(items),
        "median_minutes": round(median(waits), MINUTE_DECIMALS) if waits else None,
        "changed": sum(1 for item in items if claim_changes(item.final, item.billed) > 0),
    }


def _minutes_to_approve(item: ApprovedNote) -> float | None:
    if item.ready_at is None or item.approved_at < item.ready_at:
        return None
    return (item.approved_at - item.ready_at).total_seconds() / 60


async def _approved_notes(db: AsyncSession, practice_id: str, since: datetime) -> list[ApprovedNote]:
    rows = (
        await db.execute(
            select(Note, Provider.name, User.id, User.name, Analysis.finished_at)
            .join(Provider, Provider.id == Note.provider_id)
            .join(User, User.id == Note.approved_by)
            .outerjoin(Analysis, Analysis.id == Note.current_analysis_id)
            .where(Note.practice_id == practice_id, Note.approved_at >= since, Note.status.in_(SETTLED_STATUSES))
        )
    ).all()
    ids = [note.id for note, *_ in rows]
    final, billed = await _latest_codes(db, "final", ids), await _latest_codes(db, "billed", ids)
    return [
        ApprovedNote(
            note_id=note.id,
            provider_name=provider_name,
            approver_id=approver_id,
            approver_name=approver_name,
            place_code=note.place_code,
            service_date=note.service_date,
            ready_at=ready_at,
            approved_at=note.approved_at,
            final=final.get(note.id, ()),
            billed=billed.get(note.id, ()),
        )
        for note, provider_name, approver_id, approver_name, ready_at in rows
    ]


async def _latest_codes(db: AsyncSession, kind: str, note_ids: list[str]) -> dict[str, tuple[Code, ...]]:
    if not note_ids:
        return {}
    rows = await db.execute(
        select(CodeSet.note_id, CodeSet.codes)
        .where(CodeSet.kind == kind, CodeSet.note_id.in_(note_ids))
        .order_by(CodeSet.note_id, CodeSet.revision.desc())
        .distinct(CodeSet.note_id)
    )
    return {note_id: tuple(Code.from_json(item) for item in codes) for note_id, codes in rows}


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
