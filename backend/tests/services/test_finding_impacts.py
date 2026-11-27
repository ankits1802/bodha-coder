from datetime import date

import pytest

from app.ai.contracts import DiagnosisFinding, EmReview, ReviewReport
from app.codes.billing_codes import Code
from app.codes.icd import load_catalog
from app.services.finding_impacts import ClaimContext, amount_changes
from app.services.findings import Finding, build_findings
from app.services.routing import choices_for

SERVICE_DATE = date(2026, 11, 25)
BILLED = (Code("99215", "CPT"), Code("I10", "ICD-10"), Code("E11.9", "ICD-10"), Code("N18.30", "ICD-10"))
LEVEL_FIVE, LEVEL_FOUR = 192.39, 135.61


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
        ],
    )
    return build_findings(report, BILLED, load_catalog().for_service_date(SERVICE_DATE))


def _changes(findings: list[Finding], decided: dict[str, str], place_code: str = "11") -> dict[str, float | None]:
    return amount_changes(ClaimContext(BILLED, findings, choices_for(findings, decided), place_code, SERVICE_DATE))


def test_lowering_the_visit_level_is_priced_as_the_level_four_minus_the_level_five_amount(findings):
    assert _changes(findings, {})["em"] == pytest.approx(LEVEL_FOUR - LEVEL_FIVE)
    assert _changes(findings, {"em": "keep"})["em"] == pytest.approx(LEVEL_FOUR - LEVEL_FIVE)


def test_diagnosis_changes_move_no_money_and_questions_have_no_price(findings):
    changes = _changes(findings, {})
    assert (changes["dx:E11.9"], changes["dx:I10"], changes["dx:I12.9"]) == (0, 0, 0)
    assert changes["dx:N18.30"] is None


def test_a_place_without_a_rate_setting_prices_nothing(findings):
    assert set(_changes(findings, {}, place_code="00").values()) == {None}
