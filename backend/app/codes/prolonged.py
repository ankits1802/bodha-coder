from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

__all__ = [
    "COMMERCIAL_PROLONGED",
    "FIRST_UNIT_MINUTES",
    "MEDICARE_PROLONGED",
    "OUTSIDE_FEE_SCHEDULE",
    "PROLONGED_CODES",
    "PROLONGED_STEP_MINUTES",
    "VisitTime",
    "prolonged_problem",
    "prolonged_units",
    "prolonged_units_due",
]

COMMERCIAL_PROLONGED = "99417"
MEDICARE_PROLONGED = "G2212"
PROLONGED_STEP_MINUTES = 15
FIRST_UNIT_MINUTES: Mapping[str, Mapping[str, int]] = MappingProxyType(
    {
        COMMERCIAL_PROLONGED: MappingProxyType({"99205": 75, "99215": 55}),
        MEDICARE_PROLONGED: MappingProxyType({"99205": 89, "99215": 69}),
    }
)
PROLONGED_CODES = frozenset(FIRST_UNIT_MINUTES)
OUTSIDE_FEE_SCHEDULE = frozenset({COMMERCIAL_PROLONGED})


@dataclass(frozen=True, slots=True)
class VisitTime:
    code: str | None
    by_time: bool
    minutes: int | None


def prolonged_units(add_on: str, visit: str | None, minutes: int | None) -> int:
    start = FIRST_UNIT_MINUTES.get(add_on, {}).get(visit or "")
    if start is None or minutes is None or minutes < start:
        return 0
    return (minutes - start) // PROLONGED_STEP_MINUTES + 1


def prolonged_units_due(add_on: str, visit: VisitTime) -> int:
    return prolonged_units(add_on, visit.code, visit.minutes) if visit.by_time else 0


def prolonged_problem(add_on: str, units: int, visit: VisitTime) -> str | None:
    starts = FIRST_UNIT_MINUTES.get(add_on)
    if starts is None:
        raise ValueError(f"{add_on} is not a prolonged service code")
    if visit.code not in starts:
        return f"{add_on} is reported only with {' or '.join(starts)}, not with {visit.code or 'no visit code'}."
    if not visit.by_time or visit.minutes is None:
        return f"{add_on} needs a visit level chosen by documented total time, not by medical decision making."
    due = prolonged_units(add_on, visit.code, visit.minutes)
    if due == 0:
        return f"{visit.minutes} minutes is short of the {starts[visit.code]} minutes {add_on} needs with {visit.code}."
    if units != due:
        return f"{visit.minutes} minutes with {visit.code} is {_units(due)} of {add_on}, not {units}."
    return None


def _units(count: int) -> str:
    return f"{count} unit" if count == 1 else f"{count} units"
