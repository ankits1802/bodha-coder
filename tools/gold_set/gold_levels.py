from __future__ import annotations

import re

from gold_cases import MDM_LEVELS, GoldCase, Mdm

from app.codes.billing_codes import Code
from app.codes.em import EM_FAMILIES, EmFamily, compare_em, em_position, is_em_code
from app.codes.places import setting_for

__all__ = [
    "TELEHEALTH_MODIFIERS",
    "billed_pattern",
    "code_by_mdm",
    "code_by_time",
    "constructed_code",
    "expected_family",
    "first_em",
    "mdm_level",
    "time_decides",
]

TELEHEALTH_MODIFIERS = frozenset({"95", "93"})
FAMILY_BY_VISIT = {
    ("office", "New patient"): "office_new",
    ("office", "Established patient"): "office_established",
    ("telehealth", "New patient"): "office_new",
    ("telehealth", "Established patient"): "office_established",
    ("nursing_facility", "New patient"): "nursing_initial",
    ("nursing_facility", "Established patient"): "nursing_subsequent",
}
PATTERNS = {0: "correct", 1: "one_high", 2: "two_high", -1: "one_low", -2: "two_low"}
_FIRST_NUMBER = re.compile(r"\d+")


def mdm_level(mdm: Mdm) -> str:
    ranks = sorted(MDM_LEVELS.index(level) for level in (mdm.problems, mdm.data, mdm.risk))
    return MDM_LEVELS[ranks[1]]


def expected_family(case: GoldCase) -> EmFamily | None:
    family_id = FAMILY_BY_VISIT.get((setting_for(case.visit.place_of_service), case.visit.visit_type))
    return next((family for family in EM_FAMILIES if family.id == family_id), None)


def code_by_mdm(family: EmFamily, level: str) -> str:
    rank = MDM_LEVELS.index(level)
    leveled = [item for item in family.levels if item.mdm in MDM_LEVELS]
    reached = [item for item in leveled if MDM_LEVELS.index(item.mdm) <= rank]
    return (reached[-1] if reached else leveled[0]).code


def code_by_time(family: EmFamily, minutes: int) -> str | None:
    timed = [(int(found[0]), item.code) for item in family.levels if (found := _FIRST_NUMBER.search(item.minutes))]
    reached = [code for threshold, code in timed if threshold <= minutes]
    return reached[-1] if reached else None


def constructed_code(case: GoldCase, family: EmFamily) -> str | None:
    if case.mdm is None:
        return None
    by_mdm = code_by_mdm(family, mdm_level(case.mdm))
    by_time = code_by_time(family, case.total_minutes) if case.total_minutes else None
    if by_time is None:
        return by_mdm
    return by_time if _index(by_time) > _index(by_mdm) else by_mdm


def time_decides(case: GoldCase, family: EmFamily) -> bool:
    if case.mdm is None or not case.total_minutes:
        return False
    by_time = code_by_time(family, case.total_minutes)
    return by_time is not None and _index(by_time) > _index(code_by_mdm(family, mdm_level(case.mdm)))


def first_em(codes: tuple[Code, ...]) -> str | None:
    return next((code.code for code in codes if code.type == "CPT" and is_em_code(code.code)), None)


def billed_pattern(case: GoldCase) -> str:
    billed, expected = first_em(case.billed), first_em(case.expected)
    if expected is None:
        return "not_separately_billable" if billed else "no_visit_code"
    if billed is None:
        return "visit_code_missing"
    comparison = compare_em(billed, expected)
    if comparison.direction == "replace":
        return "other_family"
    return PATTERNS.get(comparison.level_difference, f"{comparison.level_difference:+d}_levels")


def _index(code: str) -> int:
    position = em_position(code)
    return position[1] if position else -1
