from sqlalchemy import select

from app.core.db import SessionFactory
from app.models import Analysis, NoteText
from tests.builders import marisol_report, read_next_note, reviewed_note
from tests.fakes import NOTE_TEXT, text_pdf

AMENDED = "Amended after review. " + NOTE_TEXT
SCAN = text_pdf("Signed scan")
EXTRACTED = "Amended scan. " + NOTE_TEXT


async def _replace(harness, practice, note_id: str, data: bytes, name: str = "amended.pdf"):
    return await harness.client.post(
        f"/api/notes/{note_id}/document",
        headers=practice.admin,
        files={"file": (name, data, "application/pdf")},
    )


async def _texts(note_id: str) -> list[tuple[int, str, str]]:
    async with SessionFactory() as db:
        rows = await db.scalars(select(NoteText).where(NoteText.note_id == note_id).order_by(NoteText.revision))
        return [(row.revision, row.source, row.text) for row in rows]


async def test_an_amended_pdf_replaces_the_document_and_keeps_the_old_one(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    old_key = f"practices/{practice.id}/notes/{note_id}/document.pdf"

    amended = text_pdf(AMENDED)
    replaced = await _replace(harness, practice, note_id, amended)
    assert replaced.status_code == 200, replaced.text
    assert replaced.json() == {"status": "queued"}
    assert old_key in harness.store.objects
    assert f"practices/{practice.id}/notes/{note_id}/document-r2.pdf" in harness.store.objects
    assert await _texts(note_id) == [(1, "document", NOTE_TEXT), (2, "document", AMENDED)]

    reviewer = await read_next_note(harness, icd_catalog)
    assert (reviewer.calls[-1].note_text, reviewer.calls[-1].pdf) == (AMENDED, amended)
    detail = (await harness.client.get(f"/api/notes/{note_id}", headers=practice.admin)).json()
    assert [(text["revision"], text["text"]) for text in detail["texts"]] == [(2, AMENDED)]
    assert [entry["reason"] for entry in detail["history"]["analyses"]] == ["upload", "document"]
    log = (await harness.client.get("/api/access-log", headers=practice.admin)).json()["items"]
    assert {"action": "replaced PDF", "detail": "document revision 2"} in [
        {key: entry[key] for key in ("action", "detail")} for entry in log
    ]


async def test_a_scanned_replacement_is_read_from_the_pdf_and_its_text_kept(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    assert (await _replace(harness, practice, note_id, SCAN)).status_code == 200
    assert (await _texts(note_id))[-1] == (2, "document", "")

    report = marisol_report().model_copy(update={"extracted_text": EXTRACTED})
    reviewer = await read_next_note(harness, icd_catalog, report)
    assert (reviewer.calls[-1].note_text, reviewer.calls[-1].pdf) == (None, SCAN)
    assert await _texts(note_id) == [(1, "document", NOTE_TEXT), (2, "document", ""), (3, "document", EXTRACTED)]
    async with SessionFactory() as db:
        latest = await db.scalar(select(Analysis).where(Analysis.note_id == note_id).order_by(Analysis.revision.desc()))
        assert latest.text_revision == 3

    changed = await harness.client.put(
        f"/api/notes/{note_id}/visit-type", headers=practice.admin, json={"visit_type": "New patient"}
    )
    assert changed.status_code == 200, changed.text
    again = await read_next_note(harness, icd_catalog)
    assert (again.calls[-1].note_text, again.calls[-1].pdf) == (EXTRACTED, SCAN)


async def test_a_replacement_waiting_to_be_read_supersedes_the_queued_read(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    await _replace(harness, practice, note_id, text_pdf(AMENDED))
    second = await _replace(harness, practice, note_id, text_pdf("Second amendment. " + NOTE_TEXT), "second.pdf")
    assert second.status_code == 200, second.text
    async with SessionFactory() as db:
        rows = await db.execute(select(Analysis.reason, Analysis.status).where(Analysis.note_id == note_id))
        statuses = sorted(rows.all())
    assert statuses == [("document", "queued"), ("document", "superseded"), ("upload", "succeeded")]


async def test_the_pdf_is_not_replaced_while_a_provider_question_is_open(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    asked = await harness.client.post(
        f"/api/notes/{note_id}/ask",
        headers=practice.admin,
        json={"questions": [{"key": "dx:N18.30", "text": "What stage?"}], "channel": "email", "hold": True},
    )
    assert asked.status_code == 200, asked.text
    refused = await _replace(harness, practice, note_id, text_pdf(AMENDED))
    assert refused.status_code == 409
    assert "provider request" in refused.json()["message"]


async def test_the_pdf_cannot_be_replaced_after_export_or_by_a_file_that_is_not_new(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    assert (await _replace(harness, practice, note_id, b"plain text")).status_code == 422
    same = await _replace(harness, practice, note_id, text_pdf(NOTE_TEXT))
    assert same.status_code == 409
    await harness.client.post(f"/api/notes/{note_id}/approve", headers=practice.admin)
    await harness.client.post("/api/billing/export", headers=practice.admin, json={})
    exported = await _replace(harness, practice, note_id, text_pdf(AMENDED))
    assert exported.status_code == 409
    assert await _texts(note_id) == [(1, "document", NOTE_TEXT)]
