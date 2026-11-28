from datetime import date

import pytest

from app.ai.contracts import AddOnSuggestion, EmReview, ModifierSuggestion, ReviewReport
from app.codes.billing_codes import Code
from app.codes.icd import load_catalog
from app.services.findings import Finding, build_findings
from app.services.routing import choices_for, claim, place

BILLED = (Code("99215", "CPT"), Code("20610", "CPT"), Code("M17.11", "ICD-10"))


@pytest.fixture(scope="module")
def icd():
    return load_catalog().for_service_date(date(2026, 11, 25))


def _report(code: str, modifiers: list[ModifierSuggestion], add_ons: list[AddOnSuggestion]) -> ReviewReport:
    return ReviewReport(em=EmReview(code=code, mdm_level="Moderate", modifiers=modifiers, add_on_codes=add_ons))


def _by_key(findings: list[Finding]) -> dict[str, Finding]:
    return {finding.key: finding for finding in findings}


@pytest.fixture(scope="module")
def findings(icd) -> list[Finding]:
    report = _report(
        "99214",
        [
            ModifierSuggestion(modifier="25", reason="Knee injection and a separate problem.", evidence=["knee"]),
            ModifierSuggestion(modifier="59"),
            ModifierSuggestion(modifier="XS", code="20610", reason="Separate structure."),
        ],
        [
            AddOnSuggestion(code="96127", name="Depression screening", reason="PHQ-9 scored.", evidence=["PHQ-9"]),
            AddOnSuggestion(code="99199", name="Unlisted service", reason="Not a fee schedule code."),
            AddOnSuggestion(code="20610"),
            AddOnSuggestion(code="99214"),
        ],
    )
    return build_findings(report, BILLED, icd)


def test_a_visit_modifier_goes_on_the_suggested_level(findings):
    item = _by_key(findings)["modifier:25"]
    assert (item.kind, item.action, item.code_before, item.code_after) == ("modifier", "add", "99214", "99214-25")
    assert (item.default_choice, item.evidence) == ("accept", ("knee",))


def test_a_procedure_modifier_goes_on_its_billed_code(findings):
    item = _by_key(findings)["modifier:20610:XS"]
    assert (item.action, item.code_before, item.code_after) == ("add", "20610", "20610-XS")


def test_a_modifier_outside_the_allowed_set_is_only_for_review(findings):
    item = _by_key(findings)["modifier:59"]
    assert (item.action, item.code_before, item.code_after, item.default_choice) == ("review", None, None, "keep")


def test_a_known_add_on_is_suggested_and_an_unknown_one_is_for_review(findings):
    items = _by_key(findings)
    added = items["addon:96127"]
    assert (added.kind, added.action, added.code_before, added.code_after) == ("code_review", "add", None, "96127")
    assert (added.title, added.reasoning, added.default_choice) == ("Depression screening", "PHQ-9 scored.", "accept")
    unknown = items["addon:99199"]
    assert (unknown.action, unknown.code_after, unknown.default_choice) == ("review", None, "keep")
    assert unknown.reasoning.startswith("99199 is not a 2026 physician fee schedule code.")
    assert "addon:20610" not in items
    assert "addon:99214" not in items


def test_accepted_modifiers_and_add_ons_build_the_claim(findings):
    labels = [code.label() for code in claim(BILLED, findings, choices_for(findings, {}))]
    assert labels == ["99214-25", "20610-XS", "96127", "M17.11"]


def test_keeping_leaves_the_claim_as_billed(findings):
    decisions = {"em": "keep", "modifier:25": "keep", "modifier:20610:XS": "keep", "addon:96127": "keep"}
    labels = [code.label() for code in claim(BILLED, findings, choices_for(findings, decisions))]
    assert labels == ["99215", "20610", "M17.11"]


def test_a_visit_modifier_follows_the_kept_billed_level(findings):
    labels = [code.label() for code in claim(BILLED, findings, choices_for(findings, {"em": "keep"}))]
    assert labels[0] == "99215-25"


def test_codes_and_modifiers_already_billed_are_not_suggested_again(icd):
    billed = (Code("99214", "CPT", ("25",)), Code("96127", "CPT"))
    report = _report("99214", [ModifierSuggestion(modifier="25")], [AddOnSuggestion(code="96127")])
    findings = build_findings(report, billed, icd)
    assert [item.key for item in findings] == ["em"]
    assert [code.label() for code in claim(billed, findings, choices_for(findings, {}))] == ["99214-25", "96127"]


def test_naming_the_billed_visit_code_still_targets_the_suggested_level(icd):
    report = _report("99214", [ModifierSuggestion(modifier="25", code="99215")], [])
    item = _by_key(build_findings(report, BILLED, icd))["modifier:25"]
    assert (item.code_before, item.code_after) == ("99214", "99214-25")


def test_a_modifier_for_a_code_not_on_the_claim_is_only_for_review(icd):
    report = _report("99214", [ModifierSuggestion(modifier="XS", code="11042")], [])
    item = _by_key(build_findings(report, BILLED, icd))["modifier:11042:XS"]
    assert (item.action, item.code_before) == ("review", None)


def test_a_wellness_visit_problem_code_takes_its_own_modifier(icd):
    billed = (Code("G0439", "CPT"),)
    report = _report("G0439", [ModifierSuggestion(modifier="25", code="99213")], [AddOnSuggestion(code="99213")])
    findings = build_findings(report, billed, icd)
    item = _by_key(findings)["modifier:99213:25"]
    assert (item.action, item.code_before, item.code_after) == ("add", "99213", "99213-25")
    assert [code.label() for code in claim(billed, findings, choices_for(findings, {}))] == ["G0439", "99213-25"]


def test_a_missing_modifier_or_add_on_needs_a_coder():
    modifier = Finding("modifier", "modifier:25", "add", "E/M", "", "99214", "99214-25", detail={"modifier": "25"})
    add_on = Finding("code_review", "addon:96127", "add", "Screening", "", None, "96127")
    em = Finding("em", "em", "keep", "Office visit", "", "99214", "99214", default_choice="keep")
    by_modifier = place([em, modifier], flagged=False, cleared=False, awaiting_provider=False, billed_diagnoses=True)
    by_add_on = place([em, add_on], flagged=False, cleared=False, awaiting_provider=False, billed_diagnoses=True)
    assert (by_modifier.lane, by_modifier.headline) == ("coder", "Modifier missing")
    assert (by_add_on.lane, by_add_on.headline) == ("coder", "Add-on code missing")
