from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Direction = Literal["keep", "lower", "raise", "replace", "add", "not_applicable"]


@dataclass(frozen=True)
class EmLevel:
    code: str
    mdm: str
    minutes: str


@dataclass(frozen=True)
class EmFamily:
    id: str
    label: str
    levels: tuple[EmLevel, ...]
    add_ons: tuple[EmLevel, ...] = ()


def _family(family_id: str, label: str, *levels: tuple[str, str, str]) -> EmFamily:
    return EmFamily(family_id, label, tuple(EmLevel(*level) for level in levels))


def _timed_family(family_id: str, label: str, level: tuple[str, str], add_on: tuple[str, str]) -> EmFamily:
    return EmFamily(family_id, label, (EmLevel(level[0], "", level[1]),), (EmLevel(add_on[0], "", add_on[1]),))


EM_FAMILIES: tuple[EmFamily, ...] = (
    _family(
        "office_new",
        "Office visit, new patient",
        ("99202", "Straightforward", "15-29"),
        ("99203", "Low", "30-44"),
        ("99204", "Moderate", "45-59"),
        ("99205", "High", "60-74"),
    ),
    _family(
        "office_established",
        "Office visit, established patient",
        ("99211", "Minimal", ""),
        ("99212", "Straightforward", "10-19"),
        ("99213", "Low", "20-29"),
        ("99214", "Moderate", "30-39"),
        ("99215", "High", "40-54"),
    ),
    _family(
        "office_consult",
        "Office consultation",
        ("99242", "Straightforward", "20"),
        ("99243", "Low", "30"),
        ("99244", "Moderate", "40"),
        ("99245", "High", "55"),
    ),
    _family(
        "nursing_initial",
        "Nursing facility, initial",
        ("99304", "Low", "25"),
        ("99305", "Moderate", "35"),
        ("99306", "High", "50"),
    ),
    _family(
        "nursing_subsequent",
        "Nursing facility, subsequent",
        ("99307", "Straightforward", "10-19"),
        ("99308", "Low", "20-29"),
        ("99309", "Moderate", "30-44"),
        ("99310", "High", "45+"),
    ),
    _family("nursing_discharge", "Nursing facility discharge", ("99315", "", "30 or less"), ("99316", "", "over 30")),
    _family(
        "inpatient_initial",
        "Hospital inpatient or observation, initial",
        ("99221", "Low", "40"),
        ("99222", "Moderate", "55"),
        ("99223", "High", "75"),
    ),
    _family(
        "inpatient_subsequent",
        "Hospital inpatient or observation, subsequent",
        ("99231", "Low", "25"),
        ("99232", "Moderate", "35"),
        ("99233", "High", "50"),
    ),
    _family(
        "inpatient_same_day",
        "Hospital inpatient or observation, admitted and discharged the same date",
        ("99234", "Low", "45"),
        ("99235", "Moderate", "70"),
        ("99236", "High", "85"),
    ),
    _family("inpatient_discharge", "Hospital discharge", ("99238", "", "30 or less"), ("99239", "", "over 30")),
    _family(
        "inpatient_consult",
        "Inpatient consultation",
        ("99252", "Straightforward", "35"),
        ("99253", "Low", "45"),
        ("99254", "Moderate", "60"),
        ("99255", "High", "80"),
    ),
    _family(
        "emergency",
        "Emergency department visit",
        ("99281", "Minimal", ""),
        ("99282", "Straightforward", ""),
        ("99283", "Low", ""),
        ("99284", "Moderate", ""),
        ("99285", "High", ""),
    ),
    _timed_family(
        "critical_care",
        "Critical care",
        ("99291", "30-74"),
        ("99292", "each additional 30 beyond the first 74"),
    ),
    _family(
        "home_new",
        "Home or residence visit, new patient",
        ("99341", "Straightforward", "15"),
        ("99342", "Low", "30"),
        ("99344", "Moderate", "60"),
        ("99345", "High", "75"),
    ),
    _family(
        "home_established",
        "Home or residence visit, established patient",
        ("99347", "Straightforward", "20"),
        ("99348", "Low", "30"),
        ("99349", "Moderate", "40"),
        ("99350", "High", "60"),
    ),
)

_BY_CODE: dict[str, tuple[EmFamily, int]] = {
    level.code: (family, index) for family in EM_FAMILIES for index, level in enumerate(family.levels)
}


@dataclass(frozen=True)
class EmComparison:
    direction: Direction
    billed: str | None
    supported: str | None
    family: str | None
    level_difference: int = 0


def em_position(code: str) -> tuple[EmFamily, int] | None:
    return _BY_CODE.get(code.strip().upper())


def is_em_code(code: str) -> bool:
    return em_position(code) is not None


def describe_em(code: str) -> str | None:
    position = em_position(code)
    if position is None:
        return None
    family, index = position
    level = family.levels[index]
    return f"{family.label} · {level.mdm}" if level.mdm else family.label


def compare_em(billed: str | None, supported: str | None) -> EmComparison:
    billed_at = em_position(billed) if billed else None
    supported_at = em_position(supported) if supported else None
    if supported_at is None:
        return EmComparison("not_applicable", billed, supported, billed_at[0].label if billed_at else None)
    family = supported_at[0].label
    if billed_at is None:
        return EmComparison("add", billed, supported, family)
    if billed_at[0].id != supported_at[0].id:
        return EmComparison("replace", billed, supported, family)
    difference = billed_at[1] - supported_at[1]
    if difference == 0:
        return EmComparison("keep", billed, supported, family)
    return EmComparison("lower" if difference > 0 else "raise", billed, supported, family, difference)
