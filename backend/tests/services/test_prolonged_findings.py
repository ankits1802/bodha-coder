from datetime import date

import pytest

from app.ai.contracts import AddOnSuggestion, EmReview, ReviewReport
from app.codes.billing_codes import parse_code_list
from app.codes.icd import load_catalog
from app.services.findings import Finding, build_findings
from app.services.routing import choices_for, claim

TIME_STATEMENT = "Total time on the date of the encounter: 70 minutes."


@pytest.fixture(scope="module")
def icd():
    return load_catalog().for_service_date(date(2026, 11, 25))


def _em(code: str, *, minutes: int | None = 70, by_time: bool = True, add_ons=()) -> EmReview:
    return EmReview(
        code=code,
        basis="Time" if by_time else "MDM",
        mdm_level="Moderate",
        time_minutes=minutes,
        evidence=[TIME_STATEMENT],
        add_on_codes=list(add_ons),
    )


def _findings(icd, billed: str, em: EmReview) -> dict[str, Finding]:
    return {item.key: item for item in build_findings(ReviewReport(em=em), parse_code_list(billed).codes, icd)}


def _claim(icd, billed: str, em: EmReview, decisions=None) -> list[str]:
    codes = parse_code_list(billed).codes
    findings = build_findings(ReviewReport(em=em), codes, icd)
    return [code.label() for code in claim(codes, findings, choices_for(findings, decisions or {}))]


def test_bodha_adds_99417_with_99215_chosen_by_time_and_the_units_the_time_gives(icd):
    em = _em("99215", add_ons=[AddOnSuggestion(code="99417", name="Prolonged service", units=2, reason="70 minutes.")])
    item = _findings(icd, "99215, I10", em)["addon:99417"]
    assert (item.action, item.code_after, item.detail["units"], item.default_choice) == ("add", "99417", 2, "accept")
    assert _claim(icd, "99215, I10", em) == ["99215", "99417 ×2", "I10"]


@pytest.mark.parametrize(
    ("em", "units", "reason"),
    [
        (_em("99214"), 1, "99417 is reported only with 99205 or 99215, not with 99214."),
        (_em("99215", by_time=False), 2, "99417 needs a visit level chosen by documented total time"),
        (_em("99215", minutes=None), 2, "99417 needs a visit level chosen by documented total time"),
        (_em("99215", minutes=50), 1, "50 minutes is short of the 55 minutes 99417 needs with 99215."),
        (_em("99215"), 1, "70 minutes with 99215 is 2 units of 99417, not 1."),
    ],
)
def test_a_99417_suggestion_that_breaks_a_rule_is_shown_for_review_and_never_added(icd, em, units, reason):
    em = em.model_copy(update={"add_on_codes": [AddOnSuggestion(code="99417", units=units)]})
    item = _findings(icd, "99215, I10", em)["addon:99417"]
    assert (item.action, item.code_after, item.default_choice) == ("review", None, "keep")
    assert reason in item.reasoning
    assert "99417" not in " ".join(_claim(icd, "99215, I10", em))


def test_the_visit_bodha_supports_decides_not_the_one_billed(icd):
    em = _em("99214", add_ons=[AddOnSuggestion(code="99417", units=2)])
    assert _findings(icd, "99215, I10", em)["addon:99417"].action == "review"


def test_g2212_follows_the_medicare_thresholds(icd):
    good = _em("99215", minutes=72, add_ons=[AddOnSuggestion(code="G2212", units=1)])
    assert _findings(icd, "99215, I10", good)["addon:G2212"].action == "add"
    early = _em("99215", minutes=60, add_ons=[AddOnSuggestion(code="G2212", units=1)])
    assert "69 minutes" in _findings(icd, "99215, I10", early)["addon:G2212"].reasoning


def test_a_billed_99417_the_time_supports_is_confirmed_and_can_be_approved(icd):
    findings = _findings(icd, "99215, 99417x2, I10", _em("99215"))
    assert "cpt:99417" not in findings
    assert not [item for item in findings.values() if item.action == "review" and item.code_before]
    assert _claim(icd, "99215, 99417x2, I10", _em("99215")) == ["99215", "99417 ×2", "I10"]


NOT_BY_TIME = "99417 needs a visit level chosen by documented total time, not by medical decision making."


@pytest.mark.parametrize(
    ("em", "reason"),
    [
        (_em("99215", by_time=False), NOT_BY_TIME),
        (_em("99215", minutes=40), "40 minutes is short of the 55 minutes 99417 needs with 99215."),
        (_em("99214"), "99417 is reported only with 99205 or 99215, not with 99214."),
    ],
)
def test_a_billed_99417_without_support_is_suggested_for_removal(icd, em, reason):
    item = _findings(icd, "99215, 99417, I10", em)["cpt:99417"]
    assert (item.kind, item.action, item.code_before, item.code_after) == ("code_review", "remove", "99417", None)
    assert (item.reasoning, item.default_choice, item.evidence) == (reason, "accept", (TIME_STATEMENT,))
    assert "99417" not in " ".join(_claim(icd, "99215, 99417, I10", em))
    assert "99417" in " ".join(_claim(icd, "99215, 99417, I10", em, {"cpt:99417": "keep"}))


def test_billed_99417_units_the_time_does_not_give_are_corrected(icd):
    item = _findings(icd, "99215, 99417, I10", _em("99215", minutes=72))["cpt:99417"]
    assert (item.action, item.code_before, item.code_after, item.detail) == ("replace", "99417", "99417", {"units": 2})
    assert item.reasoning == "72 minutes with 99215 is 2 units of 99417, not 1."
    assert _claim(icd, "99215, 99417, I10", _em("99215", minutes=72)) == ["99215", "99417 ×2", "I10"]
    assert _claim(icd, "99215, 99417, I10", _em("99215", minutes=72), {"cpt:99417": "keep"}) == [
        "99215",
        "99417",
        "I10",
    ]


def test_without_an_em_review_a_billed_99417_is_left_to_the_code_review(icd):
    codes = parse_code_list("99215, 99417, I10").codes
    assert build_findings(ReviewReport(), codes, icd) == []
