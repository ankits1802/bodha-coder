from datetime import date

import pytest

from app.ai.contracts import AddOnSuggestion, EmReview, ModifierSuggestion, ReviewReport
from app.codes.billing_codes import Code
from app.codes.icd import load_catalog
from app.services.findings import Finding, build_findings
from app.services.routing import choices_for, claim

BILLED = (Code("99215", "CPT"), Code("97597", "CPT", (), 2), Code("I10", "ICD-10"))


@pytest.fixture(scope="module")
def icd():
    return load_catalog().for_service_date(date(2026, 11, 25))


def _findings(icd, add_ons: list[AddOnSuggestion], modifiers: list[ModifierSuggestion] | None = None) -> list[Finding]:
    em = EmReview(code="99214", mdm_level="Moderate", modifiers=modifiers or [], add_on_codes=add_ons)
    return build_findings(ReviewReport(em=em), BILLED, icd)


def _by_key(findings: list[Finding]) -> dict[str, Finding]:
    return {finding.key: finding for finding in findings}


def test_an_add_on_carries_the_units_the_note_documents(icd):
    item = _by_key(_findings(icd, [AddOnSuggestion(code="96127", name="Screening", units=2)]))["addon:96127"]
    assert (item.action, item.code_after, item.detail["units"]) == ("add", "96127", 2)


def test_an_add_on_without_units_is_one_unit(icd):
    item = _by_key(_findings(icd, [AddOnSuggestion(code="96127")]))["addon:96127"]
    assert item.detail["units"] == 1


@pytest.mark.parametrize("units", [0, 100])
def test_impossible_units_are_only_for_review(icd, units):
    item = _by_key(_findings(icd, [AddOnSuggestion(code="96127", units=units)]))["addon:96127"]
    assert (item.action, item.code_after, item.default_choice) == ("review", None, "keep")
    assert f"{units} units of 96127" in item.reasoning


def test_the_claim_keeps_billed_units_and_adds_suggested_ones(icd):
    findings = _findings(icd, [AddOnSuggestion(code="96127", units=2)])
    labels = [code.label() for code in claim(BILLED, findings, choices_for(findings, {}))]
    assert labels == ["99214", "97597 ×2", "96127 ×2", "I10"]


def test_a_modifier_on_a_counted_line_keeps_its_units(icd):
    findings = _findings(icd, [], [ModifierSuggestion(modifier="XS", code="97597")])
    labels = [code.label() for code in claim(BILLED, findings, choices_for(findings, {}))]
    assert labels == ["99214", "97597-XS ×2", "I10"]


def test_skipping_an_add_on_leaves_it_off_the_claim(icd):
    findings = _findings(icd, [AddOnSuggestion(code="96127", units=2)])
    labels = [code.label() for code in claim(BILLED, findings, choices_for(findings, {"addon:96127": "keep"}))]
    assert labels == ["99214", "97597 ×2", "I10"]
