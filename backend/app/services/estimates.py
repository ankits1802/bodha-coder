from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.codes.billing_codes import Code
from app.codes.fees import ClaimEstimate, fee_schedule_for, rate_setting_for
from app.models import Note
from app.services.analysis import latest_codes

__all__ = ["claim_amount", "claim_estimate", "estimate_difference", "money", "note_estimate"]


def money(value: Decimal) -> float:
    return float(value)


def claim_estimate(codes: Iterable[Code], place_code: str, service_date: date) -> ClaimEstimate | None:
    schedule = fee_schedule_for(service_date)
    setting = rate_setting_for(place_code)
    if schedule is None or setting is None:
        return None
    return schedule.estimate(codes, setting)


def claim_amount(codes: Iterable[Code], place_code: str, service_date: date) -> float | None:
    estimate = claim_estimate(codes, place_code, service_date)
    if estimate is None or all(line.amount is None for line in estimate.lines):
        return None
    return money(estimate.total)


def estimate_difference(
    final: Iterable[Code], billed: Iterable[Code], place_code: str, service_date: date
) -> Decimal | None:
    after = claim_estimate(final, place_code, service_date)
    before = claim_estimate(billed, place_code, service_date)
    if after is None or before is None:
        return None
    return after.total - before.total


async def note_estimate(db: AsyncSession, note: Note, claim: tuple[Code, ...]) -> dict[str, Any] | None:
    billed = claim_estimate(await latest_codes(db, note.id, "billed"), note.place_code, note.service_date)
    claimed = claim_estimate(claim, note.place_code, note.service_date)
    if billed is None or claimed is None:
        return None
    return {
        "release": claimed.release,
        "setting": claimed.setting,
        "billed": _side(billed),
        "claim": _side(claimed),
        "difference": money(claimed.total - billed.total),
    }


def _side(estimate: ClaimEstimate) -> dict[str, Any]:
    return {
        "total": money(estimate.total),
        "lines": [
            {"code": line.code.label(), "amount": None if line.amount is None else money(line.amount)}
            for line in estimate.lines
        ],
        "unpriced": list(estimate.unpriced),
    }
