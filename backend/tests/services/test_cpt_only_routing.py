from datetime import date

import pytest

from app.ai.contracts import DiagnosisFinding, EmReview, ReviewReport
from app.codes.billing_codes import Code
from app.codes.icd import load_catalog
from app.services.findings import build_findings
from app.services.routing import choices_for, claim, has_diagnosis_codes, place

CPT_ONLY = (Code("99214", "CPT"),)


@pytest.fixture(scope="module")
def icd():
    return load_catalog().for_service_date(date(2026, 11, 25))


def _findings(icd, *diagnoses: DiagnosisFinding):
    report = ReviewReport(em=EmReview(code="99214", mdm_level="Moderate"), diagnoses=list(diagnoses))
    return build_findings(report, CPT_ONLY, icd)


def _supported(code: str, name: str) -> DiagnosisFinding:
    return DiagnosisFinding(name=name, icd10=code, status="supported", meat="Treated today.", evidence=[name])


def test_a_billed_list_without_icd_codes_has_no_diagnoses():
    assert has_diagnosis_codes(CPT_ONLY) is False
    assert has_diagnosis_codes((Code("99214", "CPT"), Code("I10", "ICD-10"))) is True


def test_documented_diagnoses_join_a_cpt_only_claim_without_a_coder(icd):
    diabetes = _supported("E11.65", "Type 2 diabetes with hyperglycemia")
    findings = _findings(icd, diabetes, _supported("I10", "Hypertension"))

    placed = place(findings, flagged=False, cleared=False, awaiting_provider=False, billed_diagnoses=False)

    assert (placed.lane, placed.reason, placed.headline) == ("approve", "matches", "Diagnoses added from the note")
    labels = [code.label() for code in claim(CPT_ONLY, findings, choices_for(findings, {}))]
    assert labels == ["99214", "E11.65", "I10"]


def test_the_same_additions_go_to_a_coder_when_diagnoses_were_billed(icd):
    findings = _findings(icd, _supported("I10", "Hypertension"))

    placed = place(findings, flagged=False, cleared=False, awaiting_provider=False, billed_diagnoses=True)

    assert (placed.lane, placed.reason, placed.headline) == ("coder", "code_changes", "Diagnosis missing")


def test_a_diagnosis_needing_detail_is_still_a_question(icd):
    ckd = DiagnosisFinding(
        name="CKD", icd10="N18.30", status="needs_specificity", evidence=["CKD"], suggestion="Stage not documented"
    )
    findings = _findings(icd, _supported("I10", "Hypertension"), ckd)

    placed = place(findings, flagged=False, cleared=False, awaiting_provider=False, billed_diagnoses=False)

    assert (placed.lane, placed.reason, placed.headline) == ("provider", "questions", "1 question to send")
    labels = [code.label() for code in claim(CPT_ONLY, findings, choices_for(findings, {}))]
    assert labels == ["99214", "I10"]


def test_a_visit_level_change_still_needs_a_coder_on_a_cpt_only_claim(icd):
    report = ReviewReport(em=EmReview(code="99213", mdm_level="Low"), diagnoses=[_supported("I10", "Hypertension")])
    findings = build_findings(report, CPT_ONLY, icd)

    placed = place(findings, flagged=False, cleared=False, awaiting_provider=False, billed_diagnoses=False)

    assert (placed.lane, placed.headline) == ("coder", "Billed too high")
