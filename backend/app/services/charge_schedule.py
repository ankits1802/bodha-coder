from __future__ import annotations

import csv
import io
import re
from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.codes.billing_codes import CPT_PATTERN
from app.core.deps import Actor
from app.core.errors import Invalid, NotFound
from app.models import Practice
from app.services.audit_log import record_activity

__all__ = [
    "MAX_CHARGE_CENTS",
    "MAX_CHARGES",
    "charge_list",
    "charge_schedule",
    "import_charges",
    "remove_charge",
    "set_charge",
]

SECTION = "charge_schedule"
MAX_CHARGES = 2000
MAX_CHARGE_CENTS = 9_999_999
MONEY = re.compile(r"^\$?\s*(\d{1,5}(,\d{3})*|\d+)(\.\d{1,2})?$")
CODE_COLUMNS = ("code", "cpt", "hcpcs", "procedure")
CHARGE_COLUMNS = ("charge", "fee", "amount", "price")


def charge_schedule(practice: Practice) -> dict[str, int]:
    return {str(code): int(cents) for code, cents in (practice.setup.get(SECTION) or {}).items()}


def charge_list(practice: Practice) -> dict[str, Any]:
    schedule = charge_schedule(practice)
    return {"items": [{"code": code, "cents": schedule[code]} for code in sorted(schedule)]}


async def set_charge(db: AsyncSession, actor: Actor, code: str, cents: int) -> dict[str, Any]:
    practice = await _locked_practice(db, actor)
    clean = _code(code)
    schedule = {**charge_schedule(practice), clean: _cents(cents, clean)}
    _store(practice, schedule)
    record_activity(db, actor, "charge set", practice_id=practice.id, detail=f"{clean} {_dollars(schedule[clean])}")
    await db.commit()
    return charge_list(practice)


async def remove_charge(db: AsyncSession, actor: Actor, code: str) -> dict[str, Any]:
    practice = await _locked_practice(db, actor)
    schedule = charge_schedule(practice)
    clean = code.strip().upper()
    if clean not in schedule:
        raise NotFound(f"{clean} has no charge")
    del schedule[clean]
    _store(practice, schedule)
    record_activity(db, actor, "charge removed", practice_id=practice.id, detail=clean)
    await db.commit()
    return charge_list(practice)


async def import_charges(db: AsyncSession, actor: Actor, csv_text: str) -> dict[str, Any]:
    imported = parsed_charges(csv_text)
    practice = await _locked_practice(db, actor)
    _store(practice, {**charge_schedule(practice), **imported})
    record_activity(db, actor, "charges imported", practice_id=practice.id, detail=f"{len(imported)} codes")
    await db.commit()
    return charge_list(practice)


def parsed_charges(csv_text: str) -> dict[str, int]:
    reader = csv.DictReader(io.StringIO(csv_text.strip()))
    columns = {name.strip().lower(): name for name in reader.fieldnames or [] if name}
    code_column = next((columns[name] for name in CODE_COLUMNS if name in columns), None)
    charge_column = next((columns[name] for name in CHARGE_COLUMNS if name in columns), None)
    if code_column is None or charge_column is None:
        raise Invalid("the file needs a code column and a charge column")
    found: dict[str, int] = {}
    for number, row in enumerate(reader, start=2):
        try:
            code = _code(row.get(code_column) or "")
            found[code] = _cents(_money(row.get(charge_column) or ""), code)
        except Invalid as error:
            raise Invalid(f"row {number}: {error.message}") from error
    if not found:
        raise Invalid("the file holds no charges")
    return found


def _code(code: str) -> str:
    clean = code.strip().upper()
    if CPT_PATTERN.fullmatch(clean) is None:
        raise Invalid(f"{clean or 'an empty code'} is not a CPT or HCPCS code")
    return clean


def _cents(cents: int, code: str) -> int:
    if not 0 < cents <= MAX_CHARGE_CENTS:
        raise Invalid(f"the charge for {code} must be more than $0 and at most {_dollars(MAX_CHARGE_CENTS)}")
    return cents


def _money(text: str) -> int:
    value = text.strip()
    if MONEY.fullmatch(value) is None:
        raise Invalid(f"{value or 'an empty charge'} is not an amount")
    try:
        return int(Decimal(value.replace("$", "").replace(",", "").strip()) * 100)
    except InvalidOperation as error:
        raise Invalid(f"{value} is not an amount") from error


def _dollars(cents: int) -> str:
    return f"${cents / 100:,.2f}"


def _store(practice: Practice, schedule: Mapping[str, int]) -> None:
    if len(schedule) > MAX_CHARGES:
        raise Invalid(f"a charge schedule holds at most {MAX_CHARGES} codes")
    practice.setup = {**practice.setup, SECTION: dict(sorted(schedule.items()))}


async def _locked_practice(db: AsyncSession, actor: Actor) -> Practice:
    return await db.get_one(Practice, actor.practice_id, with_for_update=True, populate_existing=True)
