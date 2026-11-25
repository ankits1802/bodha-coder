from __future__ import annotations

import pytest

from app.ai.contracts import EmReview
from app.ai.mips import MipsMeasure
from app.ai.review import review_note
from tests.ai.answers import (
    as_text,
    em_answer,
    eye_exam_measure,
    full_answer,
    hcc_answer,
    mips_answer,
    obesity_suspected,
    patient_answer,
    review_inputs,
)
from tests.fakes import FakeModelClient


async def test_modifiers_and_add_ons_keep_their_reason_and_evidence() -> None:
    em = {
        **em_answer(),
        "modifiers": [{"modifier": "25", "code": "", "reason": "Separate problem.", "evidence": ["knee pain"]}],
    }
    client = FakeModelClient([as_text({"patient": patient_answer(), "em": em})])

    report = (await review_note(client, review_inputs(sections=("em",)))).report

    assert report.em is not None
    assert [(item.modifier, item.code, item.reason) for item in report.em.modifiers] == [
        ("25", "", "Separate problem.")
    ]
    assert [(item.code, item.name, item.evidence) for item in report.em.add_on_codes] == [
        ("96127", "Depression screening", ["PHQ-9 score 4"])
    ]


def test_a_stored_report_with_bare_codes_still_reads() -> None:
    em = EmReview.model_validate({"code": "99214", "modifiers": ["25"], "add_on_codes": ["96127"]})

    assert [(item.modifier, item.code, item.reason) for item in em.modifiers] == [("25", "", "")]
    assert [(item.code, item.name) for item in em.add_on_codes] == [("96127", "")]


async def test_the_hcc_section_records_the_payment_year_and_suspected_conditions() -> None:
    client = FakeModelClient([as_text(full_answer())])

    outcome = await review_note(client, review_inputs())

    assert outcome.failed_sections == frozenset()
    hcc = outcome.report.hcc
    assert hcc is not None
    assert (hcc.model, hcc.paymentYear) == ("CMS-HCC V28", "2027")
    assert [item.icd10 for item in hcc.suspected] == ["E66.01"]
    assert hcc.suspected[0].options == [
        "Morbid (severe) obesity due to excess calories",
        "Obesity, unspecified",
        "Other",
        "Clinically undetermined",
    ]
    assert 'TASK "hcc"' in client.calls[0].prompt


async def test_a_repeated_suspected_code_is_kept_once() -> None:
    repeated = hcc_answer(obesity_suspected(), {**obesity_suspected(), "query": "Another wording."})
    client = FakeModelClient([as_text(full_answer(hcc=repeated))])

    hcc = (await review_note(client, review_inputs())).report.hcc

    assert hcc is not None
    assert [item.query for item in hcc.suspected] == [obesity_suspected()["query"]]


async def test_risk_adjustment_without_the_diagnoses_section_is_refused() -> None:
    client = FakeModelClient([])

    with pytest.raises(ValueError, match="hcc without diagnoses"):
        await review_note(client, review_inputs(sections=("hcc",)))
    assert client.calls == []


async def test_mips_measures_carry_a_documentation_status() -> None:
    met_with_a_blank = {**eye_exam_measure("Diabetes: Eye Exam"), "status": "Met"}
    client = FakeModelClient([as_text({"patient": patient_answer(), "mips": mips_answer(met_with_a_blank)})])

    report = (await review_note(client, review_inputs(sections=("mips",)))).report

    assert report.mips is not None
    assert [measure.status for measure in report.mips.eligibleMeasures] == ["missing"]


def test_mips_status_spellings_are_normalised_and_old_reports_have_none() -> None:
    base = {"measureName": "x", "mipsId": "MIPS #130", "eligibilityRationale": "r", "macro": "Reviewed today."}

    assert MipsMeasure.model_validate({**base, "status": "Not applicable"}).status == "not_applicable"
    assert MipsMeasure.model_validate({**base, "status": "met"}).status == "met"
    assert MipsMeasure.model_validate(base).status is None


async def test_the_em_prompt_lists_critical_care_same_day_stays_and_the_modifier_sets() -> None:
    client = FakeModelClient([as_text({"patient": patient_answer(), "em": em_answer()})])

    await review_note(client, review_inputs(sections=("em",)))

    prompt = client.calls[0].prompt
    assert "Critical care: 99291: 30-74 minutes; add-on 99292: each additional 30 beyond the first 74 minutes" in prompt
    assert "99234: Low MDM, 45 minutes; 99235: Moderate MDM, 70 minutes; 99236: High MDM, 85 minutes" in prompt
    assert "Medicare pays the first 99292 at 104 minutes or more in total" in prompt
    assert "- 25: Separately identifiable E/M on the same day" in prompt
    assert "- XS: Separate structure" in prompt
