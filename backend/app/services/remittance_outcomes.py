from __future__ import annotations

from collections.abc import Mapping
from datetime import date, timedelta
from typing import Any

from app.codes.adjustment_reasons import CONTRACTUAL, DOWNCODE_REASONS, PATIENT_RESPONSIBILITY
from app.codes.em import compare_em
from app.core.errors import Invalid
from app.services.payers import PLAN_TYPES
from app.services.remittance_835 import ServicePayment

__all__ = [
    "APPEALABLE",
    "DEFAULT_APPEAL_DAYS",
    "DENIED",
    "DOWNCODED",
    "OTHER",
    "PAID_AS_BILLED",
    "UNMATCHED",
    "appeal_deadline",
    "appeal_days",
    "is_downcode",
    "line_outcome",
    "plan_type_for",
    "validated_appeal_days",
]

PAID_AS_BILLED = "paid_as_billed"
DOWNCODED = "downcoded"
DENIED = "denied"
OTHER = "matched"
UNMATCHED = "unmatched"
APPEALABLE = (DOWNCODED, DENIED)
DENIED_CLAIM = "4"
COMMERCIAL = "commercial"
DEFAULT_APPEAL_DAYS: dict[str, int] = {"commercial": 180, "medicare": 120, "medicaid": 180, "other": 180}
FILING_PLAN_TYPES = {"MA": "medicare", "MB": "medicare", "MC": "medicaid"}
MAX_APPEAL_DAYS = 730


def line_outcome(line: ServicePayment, claim_status: str) -> str:
    if claim_status == DENIED_CLAIM or _unpaid(line):
        return DENIED
    if line.paid_cents < 0:
        return OTHER
    if is_downcode(line.billed_code, line.paid_code) or any(
        item.group == CONTRACTUAL and item.reason in DOWNCODE_REASONS for item in line.adjustments
    ):
        return DOWNCODED
    if line.paid_code is None or line.paid_code == line.billed_code:
        return PAID_AS_BILLED
    return OTHER


def _unpaid(line: ServicePayment) -> bool:
    owed_by_patient = sum(item.cents for item in line.adjustments if item.group == PATIENT_RESPONSIBILITY)
    return line.paid_cents == 0 and line.billed_cents > 0 and owed_by_patient == 0


def is_downcode(billed: str | None, paid: str | None) -> bool:
    if not billed or not paid or billed == paid:
        return False
    return compare_em(billed, paid).direction == "lower"


def plan_type_for(filing_indicator: str | None, listed: str | None) -> str:
    return FILING_PLAN_TYPES.get((filing_indicator or "").upper()) or listed or COMMERCIAL


def appeal_days(stored: Mapping[str, Any] | None) -> dict[str, int]:
    chosen = {key: int(value) for key, value in (stored or {}).items() if key in DEFAULT_APPEAL_DAYS}
    return {**DEFAULT_APPEAL_DAYS, **chosen}


def validated_appeal_days(values: Mapping[str, int]) -> dict[str, int]:
    unknown = set(values) - set(PLAN_TYPES)
    if unknown:
        raise Invalid(f"unknown plan types: {', '.join(sorted(unknown))}")
    for plan_type, days in values.items():
        if not 1 <= days <= MAX_APPEAL_DAYS:
            raise Invalid(f"the {plan_type} appeal window must be 1 to {MAX_APPEAL_DAYS} days")
    return dict(values)


def appeal_deadline(remitted_on: date, plan_type: str, days: Mapping[str, int]) -> date:
    return remitted_on + timedelta(days=days[plan_type])
