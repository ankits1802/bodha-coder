from __future__ import annotations

import copy
import json
from collections import Counter

import pytest
from gold_cases import CASES_FILE, GoldSetInvalid, Mdm, load_gold_set, parse_gold_set
from gold_checks import CodeSets, check_gold_set, pipeline_can_express
from gold_levels import billed_pattern, code_by_mdm, code_by_time, mdm_level, prolonged_units

from app.codes.em import EM_FAMILIES
from app.codes.em_benchmarks import default_em_benchmarks
from app.codes.ncci import ncci_tables

FAMILIES = {family.id: family for family in EM_FAMILIES}


@pytest.fixture(scope="module")
def code_sets(icd_catalog) -> CodeSets:
    return CodeSets(icd_catalog, ncci_tables(), default_em_benchmarks())


@pytest.fixture(scope="module")
def raw() -> dict:
    return json.loads(CASES_FILE.read_text(encoding="utf-8"))


def problems_after(raw: dict, code_sets: CodeSets, case_id: str, change) -> list[str]:
    changed = copy.deepcopy(raw)
    change(next(case for case in changed["cases"] if case["id"] == case_id))
    return [problem for problem in check_gold_set(parse_gold_set(changed), code_sets) if problem.startswith(case_id)]


def test_the_gold_set_passes_every_check(code_sets):
    assert check_gold_set(load_gold_set(), code_sets) == []


def test_the_billing_mix_matches_the_design():
    patterns = Counter(billed_pattern(case) for case in load_gold_set().cases)
    assert patterns == {"correct": 21, "one_high": 16, "one_low": 8, "two_high": 2, "not_separately_billable": 1}


def test_every_case_is_visibly_synthetic_and_found_by_its_id():
    gold = load_gold_set()
    assert [case.patient_label for case in gold.cases[:2]] == ["Synthetic Patient 01", "Synthetic Patient 02"]
    assert gold.cases[0].file_name == "2025-10-14 - SYNTHETIC PATIENT - GS-01.pdf"
    assert all(case.id in case.file_name and "SYN" in case.mrn for case in gold.cases)
    assert all(provider.email.endswith("@example.com") for provider in gold.providers.values())


@pytest.mark.parametrize(
    ("elements", "level"),
    [
        (("Low", "Straightforward", "Moderate"), "Low"),
        (("High", "Moderate", "High"), "High"),
        (("Straightforward", "Straightforward", "Low"), "Straightforward"),
        (("Moderate", "High", "Low"), "Moderate"),
    ],
)
def test_the_mdm_level_is_met_by_two_of_three_elements(elements, level):
    assert mdm_level(Mdm(*elements)) == level


@pytest.mark.parametrize(
    ("family", "minutes", "code"),
    [
        ("office_established", 9, None),
        ("office_established", 10, "99212"),
        ("office_established", 34, "99214"),
        ("office_established", 72, "99215"),
        ("office_new", 30, "99203"),
        ("office_new", 95, "99205"),
        ("nursing_subsequent", 35, "99309"),
    ],
)
def test_time_maps_to_the_highest_level_whose_threshold_it_meets(family, minutes, code):
    assert code_by_time(FAMILIES[family], minutes) == code


def test_the_lowest_initial_nursing_facility_code_covers_straightforward_and_low():
    family = FAMILIES["nursing_initial"]
    assert [code_by_mdm(family, level) for level in ("Straightforward", "Low", "Moderate", "High")] == [
        "99304",
        "99304",
        "99305",
        "99306",
    ]


@pytest.mark.parametrize(
    ("code", "minutes", "units"),
    [("99205", 88, 0), ("99205", 89, 1), ("99205", 103, 1), ("99205", 104, 2), ("99215", 69, 1), ("99214", 90, 0)],
)
def test_medicare_prolonged_units_start_at_89_and_69_minutes(code, minutes, units):
    assert prolonged_units(code, minutes) == units


def test_a_level_the_mdm_does_not_support_is_refused(raw, code_sets):
    problems = problems_after(raw, code_sets, "GS-10", lambda case: case["mdm"].update(problems="Moderate"))
    assert problems == ["GS-10: MDM and time construct 99214, the expected claim says 99213"]


def test_a_code_not_billable_on_the_date_of_service_is_refused(raw, code_sets):
    problems = problems_after(raw, code_sets, "GS-11", lambda case: case["expected"]["claim"].__setitem__(2, "E11.2"))
    assert "GS-11: expected E11.2 is not billable in ICD-10-CM 2026" in problems


def test_a_visit_with_a_procedure_needs_modifier_25_not_an_anatomic_modifier(raw, code_sets):
    problems = problems_after(raw, code_sets, "GS-23", lambda case: case["expected"]["claim"].__setitem__(0, "99213"))
    assert "GS-23: NCCI pair 20610/99213 is not bypassed by a proper modifier" in problems


def test_a_telehealth_visit_without_its_modifier_is_refused(raw, code_sets):
    problems = problems_after(raw, code_sets, "GS-27", lambda case: case["expected"]["claim"].__setitem__(0, "99214"))
    assert "GS-27: a telehealth visit carries exactly one of 95 or 93, an in-person visit neither" in problems


def test_a_stored_shape_that_differs_from_the_harness_is_refused(raw, code_sets):
    problems = problems_after(raw, code_sets, "GS-01", lambda case: case["expected"]["scored"].update(em="99203"))
    assert len(problems) == 1 and "is not what the harness derives" in problems[0]


def test_every_expected_code_needs_a_rationale(raw, code_sets):
    problems = problems_after(raw, code_sets, "GS-01", lambda case: case["rationale"]["codes"].pop("L23.7"))
    assert problems == ["GS-01: rationale codes ['99202'] differ from the claim ['99202', 'L23.7']"]


def test_a_time_level_needs_the_minutes_in_the_note(raw, code_sets):
    problems = problems_after(raw, code_sets, "GS-22", lambda case: case.update(total_minutes=12))
    assert problems == ["GS-22: the note does not state the 12 minutes the level relies on"]


def test_unknown_fields_and_versions_are_refused(raw):
    extra = copy.deepcopy(raw)
    extra["cases"][0]["comment"] = "not allowed"
    with pytest.raises(GoldSetInvalid, match="unknown \\['comment'\\]"):
        parse_gold_set(extra)
    with pytest.raises(GoldSetInvalid, match="schemaVersion 2"):
        parse_gold_set({**raw, "schemaVersion": 2})


def test_only_a_removed_visit_line_or_modifier_is_beyond_bodhas_claim():
    gold = load_gold_set()
    assert [case.id for case in gold.cases if not pipeline_can_express(case)] == ["GS-26"]
