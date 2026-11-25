from datetime import date

import pytest

from app.ai.contracts import DiagnosisFinding, EmReview, ReviewReport
from app.codes.billing_codes import Code
from app.codes.icd import load_catalog
from app.services.findings import Finding, build_findings
from app.services.routing import choices_for, claim, open_questions, place

BILLED = (Code("99215", "CPT"), Code("I10", "ICD-10"), Code("E11.9", "ICD-10"), Code("N18.30", "ICD-10"))


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


def _by_key(findings: list[Finding]) -> dict[str, Finding]:
    return {finding.key: finding for finding in findings}


def test_each_billed_and_documented_code_gets_one_suggestion(findings):
    items = _by_key(findings)
    assert (items["em"].action, items["em"].code_before, items["em"].code_after) == ("lower", "99215", "99214")
    assert (items["dx:E11.9"].action, items["dx:E11.9"].code_after) == ("replace", "E11.65")
    assert items["dx:E11.9"].reasoning == "The note documents E11.65, not E11.9."
    assert items["dx:I10"].action == "remove"
    assert (items["dx:I12.9"].action, items["dx:I12.9"].code_after) == ("add", "I12.9")
    assert items["dx:N18.30"].action == "ask"
    assert items["dx:R20.2"].action == "add"
    assert "dx:E11.65" not in items


def test_default_choices_build_the_suggested_claim(findings):
    choices = choices_for(findings, {})
    labels = [code.label() for code in claim(BILLED, findings, choices)]
    assert labels == ["99214", "E11.65", "N18.30", "I12.9", "R20.2"]


def test_keeping_the_billed_level_keeps_it_on_the_claim(findings):
    choices = choices_for(findings, {"em": "keep", "dx:I10": "keep"})
    labels = [code.label() for code in claim(BILLED, findings, choices)]
    assert labels[:2] == ["99215", "I10"]


def test_needs_detail_diagnoses_are_open_questions(findings):
    questions = open_questions(findings, choices_for(findings, {}))
    assert [item.key for item in questions] == ["dx:N18.30"]


def test_one_level_too_high_goes_to_a_coder(findings):
    placement = place(findings, flagged=False, cleared=False, awaiting_provider=False)
    assert (placement.lane, placement.headline) == ("coder", "Billed too high")


def test_two_levels_too_high_goes_to_compliance_unless_cleared():
    em = Finding("em", "em", "lower", "Nursing facility", "", "99310", "99308", detail={"level_difference": 2})
    assert place([em], flagged=False, cleared=False, awaiting_provider=False).lane == "compliance"
    assert place([em], flagged=False, cleared=True, awaiting_provider=False).lane == "coder"


def test_a_critical_audit_risk_goes_to_compliance():
    risk = Finding("audit_risk", "risk-1", "info", "Cloned note", "", severity="Critical", default_choice="keep")
    assert place([risk], flagged=False, cleared=False, awaiting_provider=False).headline == "High audit risk"


def test_matching_codes_are_ready_to_approve():
    em = Finding("em", "em", "keep", "Office visit", "", "99214", "99214", default_choice="keep")
    placement = place([em], flagged=False, cleared=False, awaiting_provider=False)
    assert (placement.lane, placement.headline) == ("approve", "Matches the note")


def test_a_pending_provider_request_waits_on_the_provider(findings):
    assert place(findings, flagged=False, cleared=False, awaiting_provider=True).lane == "provider"
