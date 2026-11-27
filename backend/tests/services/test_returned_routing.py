from datetime import date

import pytest

from app.ai.contracts import DiagnosisFinding, EmReview, ReviewReport
from app.codes.billing_codes import Code
from app.codes.icd import load_catalog
from app.core.errors import Invalid
from app.services.findings import Finding, build_findings
from app.services.note_returns import checked_return_reason, return_text, returned_items
from app.services.routing import place

BILLED = (Code("99215", "CPT"), Code("I10", "ICD-10"), Code("E11.9", "ICD-10"), Code("N18.30", "ICD-10"))
MATCH = Finding("em", "em", "keep", "Visit level", "", "99215", "99215", default_choice="keep")
RISK = Finding("audit_risk", "risk-1", "info", "Cloned note", "", severity="Critical", default_choice="keep")


def _diagnosis(code: str, status: str, name: str) -> DiagnosisFinding:
    return DiagnosisFinding(name=name, icd10=code, status=status, meat="documented", evidence=[name])


@pytest.fixture(scope="module")
def findings() -> list[Finding]:
    report = ReviewReport(
        em=EmReview(code="99214", mdm_level="Moderate", justification="Moderate decision-making."),
        diagnoses=[
            _diagnosis("E11.65", "supported", "Type 2 diabetes with hyperglycemia"),
            _diagnosis("I12.9", "supported", "Hypertensive chronic kidney disease"),
            _diagnosis("N18.30", "needs_specificity", "CKD, stable"),
            _diagnosis("R20.2", "supported", "Tingling in both feet"),
        ],
    )
    return build_findings(report, BILLED, load_catalog().for_service_date(date(2026, 11, 25)))


def _placed(items: list[Finding], **flags: bool):
    given = {"flagged": False, "cleared": False, "awaiting_provider": False, "billed_diagnoses": True, **flags}
    return place(items, **given)


def test_a_returned_match_waits_for_the_coder_instead_of_ready_to_approve():
    assert (_placed([MATCH]).lane, _placed([MATCH]).reason) == ("approve", "matches")
    returned = _placed([MATCH, RISK], cleared=True, returned=True)
    assert (returned.lane, returned.reason, returned.headline) == ("coder", "returned", "Returned")


def test_a_flag_or_a_waiting_question_still_comes_before_the_return():
    assert _placed([MATCH], flagged=True, returned=True).lane == "compliance"
    assert _placed([MATCH], awaiting_provider=True, returned=True).reason == "waiting_on_provider"


def test_the_items_to_decide_again_are_the_code_findings_with_a_choice(findings):
    hcc = Finding("diagnosis", "hcc:18", "add", "Suspected diabetes with complications", "", None, "E11.65")
    keys = returned_items([*findings, MATCH, RISK, hcc])
    assert sorted(keys) == ["dx:E11.9", "dx:I10", "dx:I12.9", "dx:N18.30", "dx:R20.2", "em"]


def test_a_return_reason_needs_a_known_reason_a_note_for_other_and_at_most_500_characters():
    assert checked_return_reason("coding_error", "  ") == checked_return_reason("coding_error", None)
    assert checked_return_reason("other", " Wrong payer ").note == "Wrong payer"
    for reason, note in (("other", " "), ("looks_fine", None), ("payer_policy", "x" * 501)):
        with pytest.raises(Invalid):
            checked_return_reason(reason, note)
    assert return_text("ask_provider", None) == "Ask the provider"
    assert return_text("level_not_supported", "MDM is moderate") == "Level not supported: MDM is moderate"
