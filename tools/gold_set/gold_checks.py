from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

from gold_cases import CASE_ID, GoldCase, GoldSet
from gold_levels import (
    TELEHEALTH_MODIFIERS,
    billed_pattern,
    constructed_code,
    expected_family,
    first_em,
    time_decides,
)

from app.codes.billing_codes import Code, is_known_cpt
from app.codes.em import is_em_code
from app.codes.em_benchmarks import EmBenchmarks, default_em_benchmarks
from app.codes.icd import IcdCatalog, IcdRelease, IcdReleaseUnavailable, load_catalog
from app.codes.modifiers import allowed_modifiers
from app.codes.ncci import AddOnEdit, NcciTables, PairEdit, ncci_tables
from app.codes.payer_rules import COMPLEXITY_ADD_ON, Payer, PayerClaim, payer_flags
from app.codes.places import SETTING_BY_PLACE
from app.codes.prolonged import COMMERCIAL_PROLONGED, MEDICARE_PROLONGED, prolonged_units
from app.services.agreement import elements_of

__all__ = [
    "REQUIRED_HEADINGS",
    "CodeSets",
    "case_categories",
    "check_case",
    "check_gold_set",
    "load_code_sets",
    "pipeline_can_express",
]

REQUIRED_HEADINGS = ("Chief complaint", "History of present illness", "Physical exam", "Assessment and plan")
MEDICARE_ONLY = frozenset({COMPLEXITY_ADD_ON, MEDICARE_PROLONGED})
ADD_ONS = MEDICARE_ONLY | {COMMERCIAL_PROLONGED}
TELEHEALTH_PLACES = frozenset(place for place, setting in SETTING_BY_PLACE.items() if setting == "telehealth")
SEPARATE_VISIT = "25"


@dataclass(frozen=True)
class CodeSets:
    icd: IcdCatalog
    ncci: NcciTables
    benchmarks: EmBenchmarks


def load_code_sets() -> CodeSets:
    return CodeSets(load_catalog(), ncci_tables(), default_em_benchmarks())


def check_gold_set(gold: GoldSet, code_sets: CodeSets) -> list[str]:
    problems = _set_problems(gold, code_sets)
    for case in gold.cases:
        problems += [f"{case.id}: {problem}" for problem in check_case(case, gold, code_sets)]
    return problems


def check_case(case: GoldCase, gold: GoldSet, code_sets: CodeSets) -> list[str]:
    try:
        release = code_sets.icd.for_service_date(case.visit.service_date)
    except IcdReleaseUnavailable as error:
        return [str(error)]
    if not code_sets.ncci.covers(case.visit.service_date):
        return [f"date of service {case.visit.service_date} is outside the loaded NCCI quarters"]
    checks: list[Callable[[], list[str]]] = [
        lambda: _visit_problems(case, gold),
        lambda: _code_problems(case.billed, release, "billed") + _code_problems(case.expected, release, "expected"),
        lambda: _scored_problems(case),
        lambda: _level_problems(case),
        lambda: _claim_rule_problems(case, code_sets.ncci),
        lambda: _rationale_problems(case),
        lambda: _note_problems(case),
    ]
    return [problem for check in checks for problem in check()]


def pipeline_can_express(case: GoldCase) -> bool:
    removes_visit = first_em(case.billed) is not None and first_em(case.expected) is None
    return not removes_visit and _modifiers(case.billed) <= _modifiers(case.expected)


def case_categories(case: GoldCase) -> tuple[str, ...]:
    family = expected_family(case)
    found = [family.id if family and first_em(case.expected) else "procedure_only", billed_pattern(case)]
    if family and first_em(case.expected):
        found.append("time" if time_decides(case, family) else "mdm")
    if case.visit.place_of_service in TELEHEALTH_PLACES:
        found.append("audio_only" if "93" in _modifiers(case.expected) else "audio_video")
    named = {code.code for code in (*case.billed, *case.expected)}
    found += ["g2211"] if COMPLEXITY_ADD_ON in named else []
    found += ["prolonged"] if named & {MEDICARE_PROLONGED, COMMERCIAL_PROLONGED} else []
    if SEPARATE_VISIT in _modifiers(case.billed) | _modifiers(case.expected):
        found.append("modifier_25")
    if _diagnoses(case.billed) != _diagnoses(case.expected):
        found.append("icd_change")
    return tuple(found)


def _set_problems(gold: GoldSet, code_sets: CodeSets) -> list[str]:
    problems = []
    numbers = [int(found[1]) if (found := CASE_ID.match(case.id)) else 0 for case in gold.cases]
    if numbers != list(range(1, len(gold.cases) + 1)):
        problems.append("case ids must run GS-01, GS-02, ... in order")
    for provider in gold.providers.values():
        if code_sets.benchmarks.specialty_for(provider.specialty) is None:
            problems.append(f"provider {provider.key}: specialty {provider.specialty} has no CMS E/M benchmark")
    return problems


def _visit_problems(case: GoldCase, gold: GoldSet) -> list[str]:
    problems = []
    if case.visit.provider not in gold.providers:
        problems.append(f"provider {case.visit.provider} is not in the providers list")
    if case.visit.place_of_service not in SETTING_BY_PLACE:
        problems.append(f"place of service {case.visit.place_of_service} has no care setting")
    elif first_em(case.expected) and expected_family(case) is None:
        problems.append("no E/M family for this place of service and visit type")
    return problems


def _code_problems(codes: tuple[Code, ...], release: IcdRelease, side: str) -> list[str]:
    problems = []
    for code in codes:
        if code.type == "ICD-10":
            entry = release.get(code.code)
            if entry is None or not entry.billable:
                problems.append(f"{side} {code.code} is not billable in ICD-10-CM {release.release}")
            continue
        if not is_known_cpt(code.code):
            problems.append(f"{side} {code.code} is not in the CMS fee schedule list or the E/M families")
        stray = [modifier for modifier in code.modifiers if modifier not in allowed_modifiers(code.code)]
        if stray:
            problems.append(f"{side} {code.code} carries modifiers Bodha does not accept there: {stray}")
    return problems


def _scored_problems(case: GoldCase) -> list[str]:
    derived = elements_of(case.expected).as_json()
    stored = {"em": case.scored.em, "icd": list(case.scored.icd), "modifiers": list(case.scored.modifiers)}
    return [] if derived == stored else [f"scored {stored} is not what the harness derives: {derived}"]


def _level_problems(case: GoldCase) -> list[str]:
    em = first_em(case.expected)
    if em is None:
        valid = case.mdm is None and case.total_minutes is None
        return [] if valid else ["a claim without an E/M code takes no MDM or time"]
    family = expected_family(case)
    if family is None or case.mdm is None:
        return ["an E/M claim needs its family and its MDM elements"]
    problems = []
    built = constructed_code(case, family)
    if built != em:
        problems.append(f"MDM and time construct {built}, the expected claim says {em}")
    prolonged = MEDICARE_PROLONGED if case.visit.payer == "medicare" else COMMERCIAL_PROLONGED
    due = prolonged_units(prolonged, em, case.total_minutes)
    claimed = sum(code.units for code in case.expected if code.code == prolonged)
    if due != claimed:
        problems.append(f"{prolonged} is due for {due} units, the expected claim has {claimed}")
    return problems


def _claim_rule_problems(case: GoldCase, ncci: NcciTables) -> list[str]:
    problems = _ncci_problems(ncci.claim_edits(case.expected, case.visit.service_date))
    named = {code.code for code in case.expected}
    if named & MEDICARE_ONLY and case.visit.payer != "medicare":
        problems.append(f"{sorted(named & MEDICARE_ONLY)} are Medicare codes on a {case.visit.payer} claim")
    if case.visit.payer == "medicare":
        flags = payer_flags(
            PayerClaim(case.expected), Payer("medicare"), case.visit.place_of_service, case.visit.service_date
        )
        problems += [f"Medicare rule {flag.rule} flags the expected claim" for flag in flags]
    return problems + _visit_modifier_problems(case)


def _ncci_problems(edits: Iterable[object]) -> list[str]:
    problems = []
    for edit in edits:
        if isinstance(edit, PairEdit):
            if edit.bypassed_by is None:
                problems.append(f"NCCI pair {edit.column1}/{edit.column2} is not bypassed by a proper modifier")
        elif isinstance(edit, AddOnEdit):
            problems.append(f"add-on {edit.code} has no primary code on the claim")
        else:
            problems.append(f"NCCI units edit: {edit}")
    return problems


def _visit_modifier_problems(case: GoldCase) -> list[str]:
    visit = next((code for code in case.expected if code.type == "CPT" and is_em_code(code.code)), None)
    if visit is None:
        return []
    problems = []
    remote = set(visit.modifiers) & TELEHEALTH_MODIFIERS
    if (case.visit.place_of_service in TELEHEALTH_PLACES) != (len(remote) == 1):
        problems.append("a telehealth visit carries exactly one of 95 or 93, an in-person visit neither")
    procedures = [code for code in case.expected if code.type == "CPT" and not is_em_code(code.code)]
    if SEPARATE_VISIT in visit.modifiers and not [code for code in procedures if code.code not in ADD_ONS]:
        problems.append("modifier 25 needs a procedure on the same claim")
    return problems


def _rationale_problems(case: GoldCase) -> list[str]:
    problems = []
    wanted = {code.code for code in case.expected}
    if set(case.rationale.codes) != wanted:
        problems.append(f"rationale codes {sorted(case.rationale.codes)} differ from the claim {sorted(wanted)}")
    if set(case.rationale.modifiers) != _modifiers(case.expected):
        problems.append(f"rationale modifiers {sorted(case.rationale.modifiers)} differ from the claim")
    return problems


def _note_problems(case: GoldCase) -> list[str]:
    headings = {section.heading for section in case.sections}
    problems = [f"the note has no {heading} section" for heading in REQUIRED_HEADINGS if heading not in headings]
    if case.total_minutes and f"{case.total_minutes} minutes" not in case.note_text():
        problems.append(f"the note does not state the {case.total_minutes} minutes the level relies on")
    return problems


def _modifiers(codes: tuple[Code, ...]) -> set[str]:
    return {modifier for code in codes if code.type == "CPT" for modifier in code.modifiers}


def _diagnoses(codes: tuple[Code, ...]) -> set[str]:
    return {code.code for code in codes if code.type == "ICD-10"}
