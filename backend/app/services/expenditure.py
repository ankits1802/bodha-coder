from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import ColumnElement, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import Invalid, NotFound
from app.core.model_prices import usd_from_microusd
from app.models import Analysis, Note, Practice, Provider
from app.services.plans import CATALOG

__all__ = ["SPEND_TIME_ZONE", "PracticeRef", "SpendRow", "expenditure", "spend_figures", "spend_report", "spend_since"]

SPEND_TIME_ZONE = "UTC"
COST_PER_NOTE_PLACES = 4
CONSUMED_TOKENS = func.coalesce(Analysis.input_tokens, 0) + func.coalesce(Analysis.output_tokens, 0) > 0


@dataclass(frozen=True)
class PracticeRef:
    id: str
    name: str
    plan: str


@dataclass(frozen=True)
class SpendRow:
    practice_id: str
    practice_name: str
    plan: str
    provider_id: str
    provider_name: str
    analyses: int
    notes: int
    input_tokens: int
    output_tokens: int
    cost_microusd: int
    unpriced: int


async def expenditure(db: AsyncSession, *, start: date, end: date, practice_id: str | None) -> dict[str, Any]:
    if end < start:
        raise Invalid("the range must end on or after the day it starts")
    conditions = [Analysis.finished_at >= _midnight(start), Analysis.finished_at < _midnight(end + timedelta(days=1))]
    listed = await _practices(db, practice_id)
    if practice_id is not None:
        if not listed:
            raise NotFound("practice not found")
        conditions.append(Note.practice_id == practice_id)
    return {
        "from": start.isoformat(),
        "to": end.isoformat(),
        "time_zone": SPEND_TIME_ZONE,
        **spend_report(await _spend_rows(db, conditions), listed),
        "unpriced_models": await _unpriced_models(db, conditions),
    }


async def _practices(db: AsyncSession, practice_id: str | None) -> list[PracticeRef]:
    query = select(Practice.id, Practice.name, Practice.plan).order_by(Practice.name, Practice.id)
    rows = await db.execute(query if practice_id is None else query.where(Practice.id == practice_id))
    return [PracticeRef(*row) for row in rows.tuples()]


async def spend_since(db: AsyncSession, since: datetime) -> dict[str, Any]:
    return spend_figures(await _spend_rows(db, [Analysis.finished_at >= since]))


def spend_report(rows: list[SpendRow], practices: Sequence[PracticeRef] = ()) -> dict[str, Any]:
    groups: dict[str, list[SpendRow]] = {}
    for row in rows:
        groups.setdefault(row.practice_id, []).append(row)
    ordered = sorted(groups.values(), key=lambda group: _rank(sum(row.cost_microusd for row in group), group[0]))
    used = [_practice_view(_practice_of(group[0]), group) for group in ordered]
    idle = [_practice_view(practice, []) for practice in practices if practice.id not in groups]
    return {
        "totals": spend_figures(rows),
        "practices": used + sorted(idle, key=lambda view: (view["name"], view["id"])),
    }


def spend_figures(rows: list[SpendRow]) -> dict[str, Any]:
    cost = sum(row.cost_microusd for row in rows)
    notes = sum(row.notes for row in rows)
    unpriced = sum(row.unpriced for row in rows)
    per_note = None if unpriced or not notes else usd_from_microusd(Decimal(cost) / notes, places=COST_PER_NOTE_PLACES)
    return {
        "analyses": sum(row.analyses for row in rows),
        "notes": notes,
        "input_tokens": sum(row.input_tokens for row in rows),
        "output_tokens": sum(row.output_tokens for row in rows),
        "cost_usd": usd_from_microusd(cost),
        "cost_per_note_usd": per_note,
        "unpriced_analyses": unpriced,
    }


def _practice_of(row: SpendRow) -> PracticeRef:
    return PracticeRef(row.practice_id, row.practice_name, row.plan)


def _practice_view(practice: PracticeRef, group: list[SpendRow]) -> dict[str, Any]:
    terms = CATALOG.get(practice.plan)
    providers = sorted(group, key=lambda row: (-row.cost_microusd, row.provider_name, row.provider_id))
    return {
        "id": practice.id,
        "name": practice.name,
        "plan": practice.plan,
        "plan_monthly_cents": terms.monthly_cents if terms else None,
        **spend_figures(group),
        "providers": [{"id": row.provider_id, "name": row.provider_name, **spend_figures([row])} for row in providers],
    }


def _rank(cost: int, row: SpendRow) -> tuple[int, str, str]:
    return -cost, row.practice_name, row.practice_id


def _midnight(day: date) -> datetime:
    return datetime.combine(day, time.min, tzinfo=UTC)


async def _spend_rows(db: AsyncSession, conditions: list[ColumnElement[bool]]) -> list[SpendRow]:
    rows = await db.execute(
        select(
            Note.practice_id,
            Practice.name,
            Practice.plan,
            Note.provider_id,
            Provider.name,
            func.count(Analysis.id),
            func.count(distinct(Analysis.note_id)),
            func.coalesce(func.sum(Analysis.input_tokens), 0),
            func.coalesce(func.sum(Analysis.output_tokens), 0),
            func.coalesce(func.sum(Analysis.cost_microusd), 0),
            func.count(Analysis.id).filter(Analysis.cost_microusd.is_(None)),
        )
        .select_from(Analysis)
        .join(Note, Note.id == Analysis.note_id)
        .join(Practice, Practice.id == Note.practice_id)
        .join(Provider, Provider.id == Note.provider_id)
        .where(CONSUMED_TOKENS, *conditions)
        .group_by(Note.practice_id, Practice.name, Practice.plan, Note.provider_id, Provider.name)
    )
    return [_spend_row(tuple(row)) for row in rows.all()]


def _spend_row(values: tuple[Any, ...]) -> SpendRow:
    names, counts = values[:5], values[5:]
    return SpendRow(*names, *(int(count) for count in counts))


async def _unpriced_models(db: AsyncSession, conditions: list[ColumnElement[bool]]) -> list[str]:
    models = await db.scalars(
        select(Analysis.model)
        .distinct()
        .select_from(Analysis)
        .join(Note, Note.id == Analysis.note_id)
        .where(CONSUMED_TOKENS, Analysis.cost_microusd.is_(None), Analysis.model.is_not(None), *conditions)
        .order_by(Analysis.model)
    )
    return [model for model in models.all() if model is not None]
