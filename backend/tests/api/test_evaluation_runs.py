from datetime import date, timedelta

import pytest
from sqlalchemy import func, select

from app.ai.contracts import AddOnSuggestion, DiagnosisFinding, EmReview, PatientFacts, ReviewReport
from app.ai.errors import ModelUnavailable
from app.ai.review import PROMPT_VERSION
from app.codes.payer_rules import Payer
from app.core.config import get_settings
from app.core.db import SessionFactory
from app.models import Analysis, CodeSet, EvalRun, NoteText, Suggestion, User
from app.services.evaluation_runs import run_evaluation
from tests.api.payer_helpers import add_payer
from tests.api.quality_helpers import SequenceReviewer, approved_note, higher_report, read_note
from tests.builders import DOCUMENTED, analysis_deps, marisol_report, practice_with_provider
from tests.fakes import FailingReviewer, ScriptedReviewer


async def evaluation_case(harness, icd_catalog):
    practice = await practice_with_provider(harness)
    note_id = await approved_note(harness, practice, icd_catalog, 1)
    added = await harness.client.post("/api/quality/eval-cases", headers=practice.admin, json={"note_id": note_id})
    assert added.status_code == 200, added.text
    return practice, note_id


async def evaluate(harness, icd_catalog, practice, reviewer) -> dict:
    queued = await harness.client.post("/api/quality/evaluations", headers=practice.admin)
    assert queued.status_code == 200, queued.text
    deps = analysis_deps(harness, icd_catalog, reviewer)
    async with SessionFactory() as db:
        assert await run_evaluation(db, queued.json()["id"], deps) is True
        assert await run_evaluation(db, queued.json()["id"], deps) is False
    return (await harness.client.get("/api/quality/evaluations", headers=practice.admin)).json()["runs"][0]


async def record_counts(note_id: str) -> tuple[int, ...]:
    async with SessionFactory() as db:
        return tuple(
            [
                await db.scalar(select(func.count()).select_from(model).where(model.note_id == note_id))
                for model in (Analysis, CodeSet, NoteText, Suggestion)
            ]
        )


async def test_an_evaluation_rereads_each_case_twice_and_leaves_the_note_alone(harness, icd_catalog):
    practice, note_id = await evaluation_case(harness, icd_catalog)
    again = await harness.client.post("/api/quality/eval-cases", headers=practice.admin, json={"note_id": note_id})
    assert again.status_code == 409
    cases = (await harness.client.get("/api/quality/eval-cases", headers=practice.admin)).json()["items"]
    assert [(case["em"], case["level"], case["icd"], case["modifiers"]) for case in cases] == [
        ("99214", "Moderate", ["E11.65", "I12.9", "N18.30", "R20.2"], [])
    ]
    before = await record_counts(note_id)

    reviewer = ScriptedReviewer(marisol_report())
    run = await evaluate(harness, icd_catalog, practice, reviewer)
    assert len(reviewer.calls) == 2
    assert reviewer.calls[0].note_text is not None
    assert await record_counts(note_id) == before
    assert (run["status"], run["model"], run["prompt_version"], run["change"]) == (
        "done",
        get_settings().gemini_model,
        PROMPT_VERSION,
        None,
    )
    summary = run["summary"]
    assert (summary["cases"], summary["scored"], summary["failed"]) == (1, 1, 0)
    assert (summary["em"]["successes"], summary["em"]["trials"], summary["icd_f1"]) == (1, 1, 1.0)
    assert summary["consistency"]["all"]["successes"] == 1
    assert summary["consistency"]["all"]["low"] == pytest.approx(0.206549, abs=1e-6)
    stored = [key for key in harness.store.objects if f"/evaluations/{run['id']}/" in key]
    assert len(stored) == 2
    detail = (await harness.client.get(f"/api/quality/evaluations/{run['id']}", headers=practice.admin)).json()
    assert (detail["results"][0]["provider_name"], detail["results"][0]["agreement"]["em"]["match"]) == (
        "Elena Varga",
        True,
    )
    note = (await harness.client.get(f"/api/notes/{note_id}", headers=practice.admin)).json()["note"]
    assert note["status"] == "approved"


async def test_an_evaluation_reads_the_billed_claim_as_uploaded_not_the_coders_edit(harness, icd_catalog):
    practice = await practice_with_provider(harness)
    note_id = await read_note(harness, practice, icd_catalog, 1)
    edited = await harness.client.put(
        f"/api/notes/{note_id}/billed-codes",
        headers=practice.admin,
        json={"codes": "99214, E11.65, I12.9, N18.30, R20.2", "reason": DOCUMENTED},
    )
    assert edited.status_code == 200, edited.text
    assert (await harness.client.post(f"/api/notes/{note_id}/approve", headers=practice.admin)).status_code == 200
    added = await harness.client.post("/api/quality/eval-cases", headers=practice.admin, json={"note_id": note_id})
    assert added.status_code == 200, added.text

    reviewer = ScriptedReviewer(marisol_report())
    run = await evaluate(harness, icd_catalog, practice, reviewer)
    assert [(code.code, code.type) for code in reviewer.calls[0].billed_codes] == [
        ("99215", "CPT"),
        ("I10", "ICD-10"),
        ("E11.9", "ICD-10"),
        ("N18.30", "ICD-10"),
    ]
    assert run["summary"]["em"]["successes"] == 1


def timed_report() -> ReviewReport:
    return ReviewReport(
        patient=PatientFacts(name="Marisol Reyes", age=52, sex="female"),
        em=EmReview(
            code="99215",
            basis="Time",
            mdm_level="Moderate",
            time_minutes=70,
            evidence=["Total time on the date of the encounter: 70 minutes."],
            add_on_codes=[
                AddOnSuggestion(code="96127", name="Depression screening", units=1),
                AddOnSuggestion(code="99417", name="Prolonged service", units=2),
            ],
        ),
        diagnoses=[DiagnosisFinding(name="Hypertension", icd10="I10", status="supported", evidence=["Hypertension"])],
    )


async def test_an_evaluation_scores_procedure_lines_add_ons_units_and_place_of_service(harness, icd_catalog):
    practice = await practice_with_provider(harness)
    note_id = await read_note(harness, practice, icd_catalog, 1, timed_report())
    edited = await harness.client.put(
        f"/api/notes/{note_id}/billed-codes",
        headers=practice.admin,
        json={"codes": "99215, 99417x2, 96127x2, I10", "reason": DOCUMENTED},
    )
    assert edited.status_code == 200, edited.text
    assert (await harness.client.post(f"/api/notes/{note_id}/approve", headers=practice.admin)).status_code == 200
    added = await harness.client.post("/api/quality/eval-cases", headers=practice.admin, json={"note_id": note_id})
    assert added.status_code == 200, added.text

    run = await evaluate(harness, icd_catalog, practice, ScriptedReviewer(timed_report()))

    summary = run["summary"]
    line_metrics = ("procedures", "add_ons", "units", "place_of_service")
    counted = [(summary[key]["successes"], summary[key]["trials"]) for key in line_metrics]
    assert counted == [(1, 1), (1, 1), (0, 1), (1, 1)]
    assert summary["units"]["high"] == pytest.approx(0.793451, abs=1e-6)
    assert summary["case_counts"] == {key: 1 for key in ("em", "icd", "modifiers", *line_metrics)}
    detail = (await harness.client.get(f"/api/quality/evaluations/{run['id']}", headers=practice.admin)).json()
    [result] = detail["results"]
    assert result["expected"]["place_of_service"] == "11"
    same = {"match": True, "scored": True}
    assert result["lines"]["procedures"] == {"reference": ["96127"], "compared": ["96127"], **same}
    assert result["lines"]["add_ons"] == {"reference": ["99417"], "compared": ["99417"], **same}
    assert result["lines"]["units"] == {
        "reference": {"96127": 2, "99417": 2},
        "compared": {"96127": 1, "99417": 2},
        "differing": ["96127"],
        "match": False,
        "scored": True,
    }


async def test_a_visit_without_procedures_scores_only_the_place_of_service_among_the_claim_lines(harness, icd_catalog):
    practice, _ = await evaluation_case(harness, icd_catalog)
    run = await evaluate(harness, icd_catalog, practice, ScriptedReviewer(marisol_report()))
    counts = run["summary"]["case_counts"]
    assert [counts[key] for key in ("procedures", "add_ons", "units", "place_of_service")] == [0, 0, 0, 1]
    assert run["summary"]["procedures"] == {"successes": 0, "trials": 0, "value": None, "low": None, "high": None}


async def test_a_run_from_before_claim_line_scoring_still_reads(harness, icd_catalog):
    practice, note_id = await evaluation_case(harness, icd_catalog)
    rate = {"successes": 1, "trials": 1, "value": 1.0, "low": 0.206549, "high": 1.0}
    comparison = {
        "em": {"reference": "99214", "compared": "99214", "match": True, "direction": "match"},
        "icd": {"matched": 1, "compared": 1, "reference": 1, "missing": [], "extra": [], "match": True},
        "modifiers": {"reference": [], "compared": [], "match": True},
    }
    async with SessionFactory() as db:
        admin = await db.scalar(select(User.id).where(User.email == "admin@lakeside.example.com"))
        expected = {"em": "99214", "icd": ["I10"], "modifiers": [], "level": None, "claim": [], "analysis_id": "a"}
        result = {"case_id": "c", "note_id": note_id, "expected": expected, "agreement": comparison}
        older = EvalRun(
            practice_id=practice.id,
            model="gemini-older",
            prompt_version="2026.11.6",
            status="done",
            results=[result],
            summary={"cases": 1, "scored": 1, "failed": 0, "em": rate, "icd_f1": 1.0, "modifiers": rate},
            requested_by=admin,
        )
        db.add(older)
        await db.commit()
        run_id = older.id

    listed = await harness.client.get("/api/quality/evaluations", headers=practice.admin)
    assert listed.status_code == 200, listed.text
    [summary] = [run["summary"] for run in listed.json()["runs"] if run["id"] == run_id]
    assert "procedures" not in summary and "case_counts" not in summary
    detail = await harness.client.get(f"/api/quality/evaluations/{run_id}", headers=practice.admin)
    assert detail.status_code == 200, detail.text
    assert "lines" not in detail.json()["results"][0]


async def test_a_drop_of_more_than_five_points_against_the_last_run_is_flagged(harness, icd_catalog):
    practice, _ = await evaluation_case(harness, icd_catalog)
    await evaluate(harness, icd_catalog, practice, ScriptedReviewer(marisol_report()))
    second = await evaluate(harness, icd_catalog, practice, ScriptedReviewer(higher_report()))
    assert second["change"]["status"] == "dropped"
    assert second["change"]["dropped"] == ["em", "icd_f1"]
    assert second["change"]["deltas"] == {"em": -1.0, "icd_f1": -1.0, "modifiers": 0.0}
    assert second["summary"]["em_higher"]["successes"] == 1


async def test_two_reads_that_disagree_lower_run_to_run_consistency(harness, icd_catalog):
    practice, _ = await evaluation_case(harness, icd_catalog)
    run = await evaluate(harness, icd_catalog, practice, SequenceReviewer([marisol_report(), higher_report()]))
    consistency = run["summary"]["consistency"]
    assert [consistency[key]["successes"] for key in ("em", "icd", "modifiers", "all")] == [0, 0, 1, 0]
    assert consistency["em"]["high"] == pytest.approx(0.793451, abs=1e-6)
    assert run["summary"]["em"]["successes"] == 1


async def test_a_case_the_model_cannot_read_is_recorded_and_fails_the_run(harness, icd_catalog):
    practice, _ = await evaluation_case(harness, icd_catalog)
    run = await evaluate(harness, icd_catalog, practice, FailingReviewer(ModelUnavailable("model down")))
    assert (run["status"], run["summary"]["scored"], run["summary"]["failed"]) == ("failed", 0, 1)
    detail = (await harness.client.get(f"/api/quality/evaluations/{run['id']}", headers=practice.admin)).json()
    assert detail["results"][0]["error"] == "model down"


async def test_only_approved_notes_join_the_set_and_an_empty_set_cannot_run(harness, icd_catalog):
    practice = await practice_with_provider(harness)
    assert (await harness.client.post("/api/quality/evaluations", headers=practice.admin)).status_code == 409
    unapproved = await read_note(harness, practice, icd_catalog, 1)
    refused = await harness.client.post("/api/quality/eval-cases", headers=practice.admin, json={"note_id": unapproved})
    assert refused.status_code == 409

    approved = await approved_note(harness, practice, icd_catalog, 2)
    candidates = (await harness.client.get("/api/quality/eval-cases/candidates", headers=practice.admin)).json()
    assert [row["note_id"] for row in candidates["items"]] == [approved]
    await harness.client.post("/api/quality/eval-cases", headers=practice.admin, json={"note_id": approved})
    assert (await harness.client.get("/api/quality/eval-cases/candidates", headers=practice.admin)).json()[
        "items"
    ] == []
    path = f"/api/quality/eval-cases/{approved}"
    assert (await harness.client.delete(path, headers=practice.admin)).status_code == 204
    assert (await harness.client.delete(path, headers=practice.admin)).status_code == 404


async def test_the_level_mix_compares_the_last_thirty_days_with_the_ninety_before(harness, icd_catalog):
    practice = await practice_with_provider(harness)
    await read_note(harness, practice, icd_catalog, 1)
    mix = (await harness.client.get("/api/quality/level-mix", headers=practice.admin)).json()
    recent = [date.fromisoformat(mix["recent"][key]) for key in ("start", "end")]
    prior = [date.fromisoformat(mix["prior"][key]) for key in ("start", "end")]
    assert (recent[1] - recent[0], prior[1] - prior[0]) == (timedelta(days=29), timedelta(days=89))
    assert prior[1] + timedelta(days=1) == recent[0]
    assert (mix["status"], mix["test"]) == ("not_enough", None)


async def _choose_payer(harness, practice, note_id: str, payer: str) -> None:
    chosen = await harness.client.put(f"/api/notes/{note_id}/payer", headers=practice.admin, json={"payer": payer})
    assert chosen.status_code == 200, chosen.text


async def test_an_evaluation_rereads_with_the_payer_the_note_had_when_it_was_approved(harness, icd_catalog):
    practice = await practice_with_provider(harness)
    medicare = await add_payer(harness, practice, "Medicare Part B", "medicare")
    aetna = await add_payer(harness, practice, "Aetna", "commercial")
    note_id = await read_note(harness, practice, icd_catalog, 1)
    await _choose_payer(harness, practice, note_id, medicare)
    assert (await harness.client.post(f"/api/notes/{note_id}/approve", headers=practice.admin)).status_code == 200
    await _choose_payer(harness, practice, note_id, aetna)
    added = await harness.client.post("/api/quality/eval-cases", headers=practice.admin, json={"note_id": note_id})
    assert added.status_code == 200, added.text

    reviewer = ScriptedReviewer(marisol_report())
    await evaluate(harness, icd_catalog, practice, reviewer)

    assert [inputs.payer for inputs in reviewer.calls] == [Payer("medicare"), Payer("medicare")]


async def test_a_case_approved_without_a_payer_is_reread_without_one(harness, icd_catalog):
    practice, _ = await evaluation_case(harness, icd_catalog)

    reviewer = ScriptedReviewer(marisol_report())
    await evaluate(harness, icd_catalog, practice, reviewer)

    assert [inputs.payer for inputs in reviewer.calls] == [None, None]
