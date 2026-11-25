from __future__ import annotations

from app.ai.review import review_note
from app.codes.mips_scope import MipsScope
from tests.ai.answers import as_text, eye_exam_measure, mips_answer, patient_answer, review_inputs
from tests.fakes import FakeModelClient

BLOOD_PRESSURE = {
    "measureName": "Controlling High Blood Pressure",
    "mipsId": "MIPS #236",
    "eligibilityRationale": "Hypertension with a recorded blood pressure.",
    "macro": "Most recent blood pressure: 148/92 on the date of service.",
    "exceptionExclusion": None,
}
WITHHELD_117 = (
    "Reporting codes not shown: the measure name on this card is not CMS's 2026 title for MIPS #117 "
    "(Diabetes: Eye Exam). Check which measure this is before reporting it."
)


async def test_d_measures_outside_the_practice_list_are_dropped() -> None:
    scope = MipsScope(measure_ids=("117",), source="practice")
    answer = {"patient": patient_answer(), "mips": mips_answer(eye_exam_measure(), BLOOD_PRESSURE)}
    client = FakeModelClient([as_text(answer)])

    report = (await review_note(client, review_inputs(sections=("mips",), scope=scope))).report

    assert report.mips is not None
    assert [measure.mipsId for measure in report.mips.eligibleMeasures] == ["MIPS #117"]
    assert report.mips.scope is not None
    assert (report.mips.scope.source, report.mips.scope.measureIds) == ("practice", ["117"])
    assert report.mips.scope.omitted == 1


async def test_d_the_prompt_names_the_practice_list() -> None:
    scope = MipsScope(measure_ids=("117",), source="practice")
    client = FakeModelClient([as_text({"patient": patient_answer(), "mips": mips_answer()})])

    await review_note(client, review_inputs(sections=("mips",), scope=scope))

    assert "# THIS PRACTICE'S MEASURE LIST" in client.calls[0].prompt
    assert "- MIPS #117 - Diabetes: Eye Exam" in client.calls[0].prompt


async def test_d_reporting_codes_come_only_from_the_table() -> None:
    invented = {"collectionType": "Invented", "specifications": [], "codes": [{"code": "9999F", "role": "met"}]}
    measure = {**eye_exam_measure(), "reportingCodes": invented, "specUrl": "https://example.test/spec"}
    client = FakeModelClient([as_text({"patient": patient_answer(), "mips": mips_answer(measure)})])

    report = (await review_note(client, review_inputs(sections=("mips",)))).report

    assert report.mips is not None
    kept = report.mips.eligibleMeasures[0]
    assert kept.reportingCodes is not None
    assert [code.code for code in kept.reportingCodes.codes][:3] == ["M1220", "M1221", "2024F"]
    assert kept.specUrl is None


async def test_d_a_title_mismatch_withholds_the_codes() -> None:
    scope = MipsScope(measure_ids=("117",), source="practice")
    answer = {"patient": patient_answer(), "mips": mips_answer(eye_exam_measure(name="Diabetic Eye Exam"))}
    client = FakeModelClient([as_text(answer)])

    report = (await review_note(client, review_inputs(sections=("mips",), scope=scope))).report

    assert report.mips is not None
    measure = report.mips.eligibleMeasures[0]
    assert measure.reportingCodes is None
    assert measure.reportingCodesWithheld == WITHHELD_117


async def test_d_a_scope_that_allows_nothing_skips_the_model() -> None:
    scope = MipsScope(measure_ids=(), source="practice", retired_ids=("999",))
    client = FakeModelClient([])

    outcome = await review_note(client, review_inputs(sections=("mips",), scope=scope))

    assert client.calls == []
    assert outcome.replies == ()
    assert outcome.failed_sections == frozenset()
    assert outcome.report.mips is not None
    assert outcome.report.mips.eligibleMeasures == []
    assert outcome.report.mips.scope is not None
    assert (outcome.report.mips.scope.measureIds, outcome.report.mips.scope.omitted) == ([], 0)
