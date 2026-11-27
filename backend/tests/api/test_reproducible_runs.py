import hashlib
import json

from sqlalchemy import select, update

from app.ai.contracts import ModelReply, ModelRequest
from app.ai.errors import ModelRequestRejected, ModelUnavailable
from app.core.config import get_settings
from app.core.db import SessionFactory
from app.models import Analysis, AnalysisFailure, Note, utcnow
from app.services.analysis import AnalysisDeps
from app.worker import process_one
from tests.builders import marisol_report, practice_with_provider
from tests.fakes import FailingReviewer, ScriptedReviewer, text_pdf

SCHEMA = {"type": "object", "properties": {"em": {"type": "object"}}}
SCHEMA_SHA256 = hashlib.sha256(b'{"properties":{"em":{"type":"object"}},"type":"object"}').hexdigest()
REQUEST = ModelRequest(prompt="Review the note below.", schema=SCHEMA, system="Answer in JSON.")
REPLY = ModelReply(
    text="{}", model="gemini-test-001", input_tokens=10, output_tokens=5, temperature=0.2, schema_applied=True
)
BILLED = "99214-25, 96127x2, I10"


async def _upload(harness, practice) -> str:
    response = await harness.client.post(
        "/api/uploads",
        headers=practice.admin,
        data={
            "provider_id": practice.provider_id,
            "service_date": "2026-11-25",
            "place_code": "11",
            "visit_type": "Established patient",
            "details": json.dumps([{"billed": BILLED}]),
        },
        files=[("files", ("2026-11-25 - visit.pdf", text_pdf("Follow-up visit."), "application/pdf"))],
    )
    assert response.status_code == 200, response.text
    return (await harness.client.get("/api/notes", headers=practice.admin)).json()["items"][0]["id"]


async def _run(note_id: str) -> tuple[Analysis, Note]:
    async with SessionFactory() as db:
        analysis = await db.scalar(select(Analysis).where(Analysis.note_id == note_id, Analysis.revision == 1))
        return analysis, await db.get_one(Note, note_id)


async def test_a_run_keeps_its_rendered_prompt_settings_code_version_codes_and_document(
    harness, icd_catalog, monkeypatch
):
    monkeypatch.setattr(get_settings(), "app_version", "2026.11.28-4f2a9c1")
    practice = await practice_with_provider(harness)
    note_id = await _upload(harness, practice)
    reviewer = ScriptedReviewer(marisol_report(), requests=(REQUEST,), replies=(REPLY,))

    assert await process_one(AnalysisDeps(reviewer, None, harness.store, icd_catalog), get_settings()) is True

    analysis, note = await _run(note_id)
    key = f"practices/{practice.id}/notes/{note_id}/analyses/1.prompt.json"
    stored = harness.store.objects[key]
    assert (analysis.prompt_key, analysis.prompt_sha256) == (key, hashlib.sha256(stored).hexdigest())
    assert json.loads(stored) == {
        "version": 1,
        "prompt_version": "test",
        "document": {"key": note.file_key, "sha256": note.file_sha256},
        "requests": [
            {
                "system": "Answer in JSON.",
                "prompt": "Review the note below.",
                "schema": SCHEMA,
                "temperature": 0.2,
                "schema_applied": True,
            }
        ],
    }
    assert analysis.generation == {
        "calls": [
            {"model": "gemini-test-001", "schema_sha256": SCHEMA_SHA256, "temperature": 0.2, "schema_applied": True}
        ]
    }
    assert (analysis.app_version, analysis.document_key) == ("2026.11.28-4f2a9c1", note.file_key)
    assert analysis.context["billed"] == [
        {"code": "99214", "type": "CPT", "modifiers": ["25"], "units": 1},
        {"code": "96127", "type": "CPT", "modifiers": [], "units": 2},
        {"code": "I10", "type": "ICD-10", "modifiers": [], "units": 1},
    ]


async def test_each_failed_attempt_keeps_its_own_error(harness, icd_catalog):
    practice = await practice_with_provider(harness)
    note_id = await _upload(harness, practice)
    busy = FailingReviewer(ModelUnavailable("Gemini generate_content failed after retries (ServerError)."))
    refused = FailingReviewer(ModelRequestRejected("The Gemini account has no credits left (HTTP 402)."))

    assert await process_one(AnalysisDeps(busy, None, harness.store, icd_catalog), get_settings()) is True
    async with SessionFactory() as db:
        await db.execute(update(Analysis).where(Analysis.note_id == note_id).values(requested_at=utcnow()))
        await db.commit()
    assert await process_one(AnalysisDeps(refused, None, harness.store, icd_catalog), get_settings()) is True

    analysis, _ = await _run(note_id)
    async with SessionFactory() as db:
        query = select(AnalysisFailure).where(AnalysisFailure.analysis_id == analysis.id)
        failures = (await db.scalars(query.order_by(AnalysisFailure.attempt))).all()
    assert [(row.attempt, row.error, row.retried) for row in failures] == [
        (1, "Gemini generate_content failed after retries (ServerError).", True),
        (2, "The Gemini account has no credits left (HTTP 402).", False),
    ]
    assert (analysis.status, analysis.error) == ("failed", "The Gemini account has no credits left (HTTP 402).")
