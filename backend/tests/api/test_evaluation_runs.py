from datetime import date, timedelta

import pytest
from sqlalchemy import func, select

from app.ai.errors import ModelUnavailable
from app.ai.review import PROMPT_VERSION
from app.core.config import get_settings
from app.core.db import SessionFactory
from app.models import Analysis, CodeSet, NoteText, Suggestion
from app.services.evaluation_runs import run_evaluation
from tests.api.quality_helpers import SequenceReviewer, approved_note, higher_report, read_note
from tests.builders import analysis_deps, marisol_report, practice_with_provider
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
