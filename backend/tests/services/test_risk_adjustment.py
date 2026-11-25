from datetime import date

import pytest

from app.ai.contracts import DiagnosisFinding, EmReview, PatientFacts, ReviewReport
from app.ai.hcc import HccReview, SuspectedCondition
from app.codes.billing_codes import Code
from app.codes.hcc import HccCategory, HccInteraction, HccMapping, HccModel
from app.codes.icd import load_catalog
from app.services.findings import build_findings
from app.services.risk_adjustment import risk_adjustment_findings
from app.services.routing import choices_for, open_questions, place

BILLED = (Code("99214", "CPT"), Code("E11.9", "ICD-10"), Code("I50.22", "ICD-10"))


def _factors(aged: float, disabled: float) -> dict[str, float]:
    return {"aged": aged, "disabled": disabled}


@pytest.fixture(scope="module")
def model() -> HccModel:
    categories = {
        "HCC37": HccCategory("HCC37", "Diabetes with Complications", _factors(0.166, 0.191), ("HCC38",), ("DM",)),
        "HCC38": HccCategory("HCC38", "Diabetes without Complications", _factors(0.166, 0.191), (), ("DM",)),
        "HCC48": HccCategory("HCC48", "Morbid Obesity", _factors(0.186, 0.144)),
        "HCC226": HccCategory("HCC226", "Heart Failure", _factors(0.36, 0.442), (), ("HF",)),
        "HCC328": HccCategory("HCC328", "Chronic Kidney Disease, Stage 3B", _factors(0.127, 0.179)),
    }
    mappings = {
        "E119": (HccMapping("HCC38"),),
        "E1122": (HccMapping("HCC37"),),
        "E6601": (HccMapping("HCC48"),),
        "I5022": (HccMapping("HCC226"),),
        "N1832": (HccMapping("HCC328"),),
    }
    return HccModel(
        "2027",
        mappings,
        categories,
        counts={count: _factors(0, 0) for count in range(1, 11)},
        interactions=(HccInteraction("DM_HF", _factors(0.112, 0.023), ("DM", "HF")),),
    )


@pytest.fixture(scope="module")
def icd():
    return load_catalog().for_service_date(date(2026, 11, 25))


def _supported(code: str, name: str) -> DiagnosisFinding:
    return DiagnosisFinding(name=name, icd10=code, status="supported", evidence=[name])


def _suspected(code: str) -> SuspectedCondition:
    return SuspectedCondition(condition="CKD", icd10=code, query="eGFR 38 and 40. Please clarify.", options=["A", "B"])


def _report(age: int | None, *suspected: SuspectedCondition) -> ReviewReport:
    return ReviewReport(
        patient=PatientFacts(age=age, sex="female"),
        em=EmReview(code="99214", mdm_level="Moderate"),
        diagnoses=[
            _supported("E11.22", "Type 2 diabetes with diabetic chronic kidney disease"),
            _supported("I50.22", "Chronic systolic heart failure"),
            _supported("E66.01", "Morbid obesity"),
        ],
        hcc=HccReview(paymentYear="2027", suspected=list(suspected)),
    )


def _summary(findings):
    return next(item for item in findings if item.key == "hcc")


def test_categories_are_captured_or_missed_and_scored_from_the_factors(model, icd):
    findings = risk_adjustment_findings(_report(70), BILLED, icd, model)
    detail = _summary(findings).detail
    assert detail["segment"] == "Community, non-dual, aged"
    assert (detail["score_billed"], detail["score_documented"]) == (0.638, 0.824)
    assert [(row["hcc"], row["status"], row["codes"], row["factor"]) for row in detail["categories"]] == [
        ("HCC37", "missed", ["E11.22"], 0.166),
        ("HCC48", "missed", ["E66.01"], 0.186),
        ("HCC226", "captured", ["I50.22"], 0.36),
    ]


def test_a_billed_category_without_documentation_is_unsupported(model, icd):
    report = _report(70).model_copy(update={"diagnoses": [_supported("I50.22", "Chronic systolic heart failure")]})
    rows = _summary(risk_adjustment_findings(report, BILLED, icd, model)).detail["categories"]
    assert [(row["hcc"], row["status"]) for row in rows] == [("HCC38", "unsupported"), ("HCC226", "captured")]


def test_without_an_age_categories_are_listed_without_scores(model, icd):
    detail = _summary(risk_adjustment_findings(_report(None), BILLED, icd, model)).detail
    assert (detail["segment"], detail["score_billed"], detail["score_documented"]) == (None, None, None)
    assert [row["factor"] for row in detail["categories"]] == [None, None, None]


def test_suspected_conditions_become_questions_only_when_new_and_risk_adjusting(model, icd):
    report = _report(70, _suspected("N18.32"), _suspected("I50.22"), _suspected("I10"), _suspected("E11.9"))
    findings = risk_adjustment_findings(report, BILLED, icd, model)
    asked = [item for item in findings if item.key.startswith("hcc:")]
    assert [item.key for item in asked] == ["hcc:N18.32"]
    item = asked[0]
    assert (item.kind, item.action, item.code_before, item.code_after) == ("diagnosis", "ask", None, None)
    assert (item.title, item.default_choice) == ("eGFR 38 and 40. Please clarify.", "ask")
    assert item.detail["hccs"] == [{"hcc": "HCC328", "label": "Chronic Kidney Disease, Stage 3B"}]
    assert item.detail["options"] == ["A", "B", "Clinically undetermined"]


def test_without_a_vendored_model_only_the_unavailable_summary_is_shown(icd):
    findings = risk_adjustment_findings(_report(70, _suspected("N18.32")), BILLED, icd, None)
    assert [(item.key, item.detail["available"]) for item in findings] == [("hcc", False)]


def test_the_summary_is_not_a_code_change_and_suspected_items_are_questions(model, icd):
    report = _report(70, _suspected("N18.32"))
    findings = risk_adjustment_findings(report, BILLED, icd, model)
    placed = place(findings, flagged=False, cleared=False, awaiting_provider=False, billed_diagnoses=True)
    assert (placed.lane, placed.reason) == ("provider", "questions")
    assert [item.key for item in open_questions(findings, choices_for(findings, {}))] == ["hcc:N18.32"]


def test_build_findings_uses_the_vendored_cms_model(icd):
    report = _report(70)
    detail = _summary(build_findings(report, BILLED, icd)).detail
    assert (detail["model"], detail["payment_year"], detail["available"]) == ("CMS-HCC V28", "2027", True)
    assert [(row["hcc"], row["status"]) for row in detail["categories"]] == [
        ("HCC37", "missed"),
        ("HCC48", "missed"),
        ("HCC226", "captured"),
    ]
