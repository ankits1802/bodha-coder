import pytest

from app.codes.billing_codes import parse_code_list
from app.services.evaluation_scores import evaluation_summary
from app.services.line_agreement import compare_lines, lines_from_expected, lines_of, summarize_lines

SAME_ELEMENTS = {
    "em": {"reference": "99214", "compared": "99214", "match": True, "direction": "match"},
    "icd": {"matched": 1, "compared": 1, "reference": 1, "missing": [], "extra": [], "match": True},
    "modifiers": {"reference": [], "compared": [], "match": True},
}


def _lines(text: str, place: str | None = "11"):
    return lines_of(parse_code_list(text).codes, place)


def test_the_visit_code_is_left_out_and_add_ons_are_kept_apart_from_procedures():
    lines = _lines("99215-25, 20610-RT, G2211, 99417x2, 96127x2, M17.11")
    assert lines.as_json() == {
        "procedures": ["20610", "96127"],
        "add_ons": ["99417", "G2211"],
        "units": {"20610": 1, "96127": 2, "99417": 2, "G2211": 1},
        "place_of_service": "11",
    }


def test_a_code_on_two_lines_adds_its_units():
    codes = (*parse_code_list("20610-RT").codes, *parse_code_list("20610-LT").codes)
    assert lines_of(codes, "11").units == {"20610": 2}


def test_procedures_and_add_ons_are_scored_only_when_either_claim_has_one():
    found = compare_lines(_lines("99214, I10"), _lines("99214, I10"))
    assert [found[key]["scored"] for key in ("procedures", "add_ons", "units", "place_of_service")] == [
        False,
        False,
        False,
        True,
    ]
    extra = compare_lines(_lines("99214, I10"), _lines("99214, 96127, I10"))
    assert extra["procedures"] == {"reference": [], "compared": ["96127"], "match": False, "scored": True}


def test_units_are_compared_on_the_lines_both_claims_carry():
    found = compare_lines(_lines("99215, 99417x2, 96127x2"), _lines("99215, 99417x2, 96127, 20610"))
    assert found["units"] == {
        "reference": {"96127": 2, "99417": 2},
        "compared": {"96127": 1, "99417": 2},
        "differing": ["96127"],
        "match": False,
        "scored": True,
    }
    assert found["procedures"]["match"] is False
    assert found["add_ons"]["match"] is True


def test_the_place_of_service_is_compared_as_it_stands():
    found = compare_lines(_lines("99214", "10"), _lines("99214", "02"))
    assert found["place_of_service"] == {"reference": "10", "compared": "02", "match": False, "scored": True}


def test_the_reference_comes_from_the_approved_claim_and_its_place_of_service():
    claim = [code.as_json() for code in parse_code_list("99215, 99417x2, I10").codes]
    recorded = lines_from_expected({"claim": claim, "place_of_service": "02"}, "11")
    assert recorded is not None
    assert (recorded.add_ons, recorded.units, recorded.place_of_service) == (frozenset({"99417"}), {"99417": 2}, "02")
    older = lines_from_expected({"claim": claim}, "11")
    assert older is not None and older.place_of_service == "11"
    assert lines_from_expected({"em": "99215"}, "11") is None


def test_each_line_metric_has_its_own_case_count_and_wilson_interval():
    comparisons = [
        compare_lines(_lines("99214, 20610"), _lines("99214, 20610")),
        compare_lines(_lines("99214, 20610"), _lines("99214, 20611")),
        compare_lines(_lines("99214"), _lines("99214")),
    ]
    rates = summarize_lines(comparisons)
    assert (rates["procedures"]["successes"], rates["procedures"]["trials"]) == (1, 2)
    assert (rates["units"]["successes"], rates["units"]["trials"]) == (1, 1)
    assert (rates["add_ons"]["successes"], rates["add_ons"]["trials"]) == (0, 0)
    assert rates["add_ons"]["value"] is None
    assert (rates["place_of_service"]["successes"], rates["place_of_service"]["trials"]) == (3, 3)
    assert rates["procedures"]["low"] == pytest.approx(0.094531, abs=1e-6)


def test_the_summary_counts_cases_per_metric_and_skips_results_without_claim_lines():
    with_lines = {
        "agreement": SAME_ELEMENTS,
        "repeat": SAME_ELEMENTS,
        "lines": compare_lines(_lines("99215, 99417"), _lines("99215, 99417")),
    }
    older = {"agreement": SAME_ELEMENTS, "repeat": SAME_ELEMENTS}
    failed = {"error": "model down"}
    summary = evaluation_summary([with_lines, older, failed])
    assert (summary["cases"], summary["scored"], summary["failed"]) == (3, 2, 1)
    assert summary["case_counts"] == {
        "em": 2,
        "icd": 2,
        "modifiers": 2,
        "procedures": 0,
        "add_ons": 1,
        "units": 1,
        "place_of_service": 1,
    }
    assert (summary["add_ons"]["successes"], summary["add_ons"]["trials"]) == (1, 1)
    assert summary["em"]["trials"] == 2
