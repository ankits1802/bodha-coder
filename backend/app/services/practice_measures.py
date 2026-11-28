from __future__ import annotations

from collections.abc import Collection, Mapping
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.codes.practice_measures import (
    PracticeMeasureDefinition,
    PracticeMeasureRejected,
    checked_codes,
    checked_identifier,
    checked_name,
    checked_text,
    key_for,
    key_number,
    required_text,
)
from app.core.deps import Actor
from app.core.errors import Conflict, Invalid, NotFound
from app.models import MipsList, PracticeMeasure
from app.services.audit_log import record_activity

__all__ = [
    "LIVE_MEASURE_LIMIT",
    "MeasureValues",
    "add_measure",
    "change_measure",
    "checked_values",
    "definitions_by_version",
    "definition_of",
    "definitions_for",
    "live_measures",
    "measure_view",
    "retire_measure",
]

LIVE_MEASURE_LIMIT = 25
RACED = "someone else changed the practice measures at the same time; reload and try again"
STALE = "someone else changed this measure; reload and try again"


@dataclass(frozen=True)
class MeasureValues:
    name: str
    identifier: str | None
    in_scope: str
    out_of_scope: str | None
    to_meet: str
    met_codes: tuple[str, ...]
    not_met_codes: tuple[str, ...]


def checked_values(raw: Mapping[str, Any]) -> MeasureValues:
    try:
        met, not_met = checked_codes(raw["met_codes"], raw["not_met_codes"])
        return MeasureValues(
            name=checked_name(raw["name"]),
            identifier=checked_identifier(raw["identifier"]),
            in_scope=required_text(raw["in_scope"], "what puts a visit in scope"),
            out_of_scope=checked_text(raw["out_of_scope"], "what takes a visit out of scope"),
            to_meet=required_text(raw["to_meet"], "what the note must document"),
            met_codes=met,
            not_met_codes=not_met,
        )
    except PracticeMeasureRejected as error:
        raise Invalid(error.message) from error


async def live_measures(db: AsyncSession, practice_id: str) -> list[PracticeMeasure]:
    return [row for row in await _latest_versions(db, practice_id) if not row.retired]


async def add_measure(db: AsyncSession, actor: Actor, values: MeasureValues) -> PracticeMeasure:
    latest = await _latest_versions(db, actor.practice_id)
    live = [row for row in latest if not row.retired]
    if len(live) >= LIVE_MEASURE_LIMIT:
        raise Invalid(f"a practice keeps at most {LIVE_MEASURE_LIMIT} measures of its own; retire one first")
    _refuse_taken_name(live, values.name, key=None)
    try:
        key = key_for(max((key_number(row.measure_key) for row in latest), default=0) + 1)
    except PracticeMeasureRejected as error:
        raise Invalid(error.message) from error
    row = _version_row(actor, key, 1, values)
    await _keep(db, actor, row, "practice measure added")
    return row


async def change_measure(
    db: AsyncSession, actor: Actor, key: str, values: MeasureValues, *, expected_version: int
) -> PracticeMeasure:
    current = await _live_measure(db, actor.practice_id, key, expected_version)
    if _values_of(current) == values:
        return current
    _refuse_taken_name(await live_measures(db, actor.practice_id), values.name, key=key)
    row = _version_row(actor, key, current.version + 1, values)
    await _keep(db, actor, row, "practice measure changed")
    return row


async def retire_measure(db: AsyncSession, actor: Actor, key: str, *, expected_version: int) -> None:
    current = await _live_measure(db, actor.practice_id, key, expected_version)
    listed = await db.scalar(select(MipsList.measure_ids).where(MipsList.practice_id == actor.practice_id))
    if key in (listed or []):
        raise Conflict("this measure is on the measure list; take it off and save the list before retiring it")
    row = _version_row(actor, key, current.version + 1, _values_of(current), retired=True)
    await _keep(db, actor, row, "practice measure retired")


async def definitions_for(
    db: AsyncSession, practice_id: str, keys: Collection[str]
) -> dict[str, PracticeMeasureDefinition]:
    if not keys:
        return {}
    rows = await live_measures(db, practice_id)
    return {row.measure_key: definition_of(row) for row in rows if row.measure_key in keys}


async def definitions_by_version(
    db: AsyncSession, version_ids: Collection[str]
) -> dict[str, PracticeMeasureDefinition]:
    if not version_ids:
        return {}
    rows = await db.scalars(select(PracticeMeasure).where(PracticeMeasure.id.in_(list(version_ids))))
    return {row.measure_key: definition_of(row) for row in rows}


def definition_of(row: PracticeMeasure) -> PracticeMeasureDefinition:
    return PracticeMeasureDefinition(
        key=row.measure_key,
        version=row.version,
        version_id=row.id,
        name=row.name,
        identifier=row.identifier,
        in_scope=row.in_scope,
        out_of_scope=row.out_of_scope,
        to_meet=row.to_meet,
        met_codes=tuple(row.met_codes),
        not_met_codes=tuple(row.not_met_codes),
    )


def measure_view(row: PracticeMeasure) -> dict[str, Any]:
    return {
        "key": row.measure_key,
        "version": row.version,
        "name": row.name,
        "identifier": row.identifier,
        "in_scope": row.in_scope,
        "out_of_scope": row.out_of_scope,
        "to_meet": row.to_meet,
        "met_codes": list(row.met_codes),
        "not_met_codes": list(row.not_met_codes),
        "changed_at": row.created_at.isoformat(),
    }


async def _latest_versions(db: AsyncSession, practice_id: str) -> list[PracticeMeasure]:
    rows = await db.scalars(
        select(PracticeMeasure)
        .where(PracticeMeasure.practice_id == practice_id)
        .order_by(PracticeMeasure.measure_key, PracticeMeasure.version.desc())
        .distinct(PracticeMeasure.measure_key)
    )
    return list(rows)


async def _live_measure(db: AsyncSession, practice_id: str, key: str, expected_version: int) -> PracticeMeasure:
    current = next((row for row in await live_measures(db, practice_id) if row.measure_key == key), None)
    if current is None:
        raise NotFound("no such practice measure")
    if current.version != expected_version:
        raise Conflict(STALE)
    return current


def _refuse_taken_name(live: list[PracticeMeasure], name: str, *, key: str | None) -> None:
    wanted = name.casefold()
    if any(row.name.casefold() == wanted and row.measure_key != key for row in live):
        raise Invalid("another practice measure already has this name")


def _values_of(row: PracticeMeasure) -> MeasureValues:
    return MeasureValues(
        name=row.name,
        identifier=row.identifier,
        in_scope=row.in_scope,
        out_of_scope=row.out_of_scope,
        to_meet=row.to_meet,
        met_codes=tuple(row.met_codes),
        not_met_codes=tuple(row.not_met_codes),
    )


def _version_row(
    actor: Actor, key: str, version: int, values: MeasureValues, *, retired: bool = False
) -> PracticeMeasure:
    return PracticeMeasure(
        practice_id=actor.practice_id,
        measure_key=key,
        version=version,
        name=values.name,
        identifier=values.identifier,
        in_scope=values.in_scope,
        out_of_scope=values.out_of_scope,
        to_meet=values.to_meet,
        met_codes=list(values.met_codes),
        not_met_codes=list(values.not_met_codes),
        retired=retired,
        created_by=actor.user.id,
    )


async def _keep(db: AsyncSession, actor: Actor, row: PracticeMeasure, action: str) -> None:
    db.add(row)
    record_activity(db, actor, action, practice_id=actor.practice_id, detail=f"{row.measure_key} version {row.version}")
    try:
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise Conflict(RACED) from error
