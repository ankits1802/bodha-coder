import hashlib

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.core.db import SessionFactory
from app.models import Analysis, ApprovedClaim, ClaimExport, ClaimExportItem, CodeSet, Note, NoteText, User
from tests.api.review_helpers import approve, keep_i10_with_reason
from tests.builders import reviewed_note

FINAL = ["99214", "I10", "E11.65", "N18.30", "I12.9", "R20.2"]


async def _snapshots(note_id: str) -> list[ApprovedClaim]:
    async with SessionFactory() as db:
        query = select(ApprovedClaim).where(ApprovedClaim.note_id == note_id).order_by(ApprovedClaim.revision)
        return list((await db.scalars(query)).all())


async def _approved(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    await keep_i10_with_reason(harness, practice, note_id)
    assert (await approve(harness, practice, note_id)).status_code == 200
    return practice, note_id


async def test_approval_freezes_the_claim_its_decisions_and_its_provenance(harness, icd_catalog):
    practice, note_id = await _approved(harness, icd_catalog)
    [snapshot] = await _snapshots(note_id)
    async with SessionFactory() as db:
        note = await db.get_one(Note, note_id)
        analysis = await db.get_one(Analysis, note.current_analysis_id)
        texts = (await db.scalars(select(NoteText.id).where(NoteText.note_id == note_id))).all()
        admin = await db.scalar(select(User).where(User.email == "admin@lakeside.example.com"))
    content = snapshot.content
    assert [item["code"] for item in content["codes"]] == FINAL
    assert content["em"] == {"code": "99214", "modifiers": [], "units": 1}
    assert content["diagnoses"] == [
        {"letter": letter, "code": code} for letter, code in zip("ABCDE", FINAL[1:], strict=True)
    ]
    assert content["procedures"] == [
        {"code": "99214", "modifiers": [], "units": 1, "pointers": FINAL[1:5], "letters": ["A", "B", "C", "D"]}
    ]
    assert [item["code"] for item in content["billed"]] == ["99215", "I10", "E11.9", "N18.30"]
    assert content["billed_original"] == content["billed"] and content["billed_revision"] == 1
    assert [(d["key"], d["choice"], d["override_reason"], d["departs"]) for d in content["decisions"]] == [
        ("dx:I10", "keep", "documentation", True)
    ]
    assert (snapshot.approved_by, snapshot.approver_name, snapshot.approver_role) == (admin.id, admin.name, "admin")
    assert (snapshot.analysis_id, snapshot.model, snapshot.prompt_version) == (
        analysis.id,
        analysis.model,
        analysis.prompt_version,
    )
    assert snapshot.text_revision_ids == list(texts)
    assert (snapshot.document_key, snapshot.document_sha256) == (note.file_key, note.file_sha256)
    assert snapshot.approved_at == note.approved_at


async def test_reopening_and_approving_again_adds_a_revision_and_keeps_the_first(harness, icd_catalog):
    practice, note_id = await _approved(harness, icd_catalog)
    [first] = await _snapshots(note_id)
    assert (await harness.client.post(f"/api/notes/{note_id}/reopen", headers=practice.admin)).status_code == 200
    assert (await approve(harness, practice, note_id)).status_code == 200

    snapshots = await _snapshots(note_id)

    assert [row.revision for row in snapshots] == [1, 2]
    assert (snapshots[0].id, snapshots[0].content, snapshots[0].approved_at) == (
        first.id,
        first.content,
        first.approved_at,
    )
    history = (await harness.client.get(f"/api/notes/{note_id}", headers=practice.admin)).json()["history"]
    assert [row["revision"] for row in history["snapshots"]] == [1, 2]


async def test_a_snapshot_cannot_be_updated_in_place(harness, icd_catalog):
    _, note_id = await _approved(harness, icd_catalog)
    async with SessionFactory() as db:
        with pytest.raises(DBAPIError, match="append-only"):
            await db.execute(text("UPDATE approved_claims SET approver_name = 'someone else'"))


async def test_an_export_uses_the_snapshot_not_the_live_codes(harness, icd_catalog):
    practice, note_id = await _approved(harness, icd_catalog)
    async with SessionFactory() as db:
        live = [{"code": "99205", "type": "CPT", "modifiers": [], "units": 1}]
        db.add(CodeSet(note_id=note_id, kind="final", revision=2, codes=live, reason="tampered"))
        await db.commit()

    exported = await harness.client.post("/api/billing/export", headers=practice.admin, json={})

    assert exported.status_code == 200, exported.text
    assert ",99214,I10 E11.65 N18.30 I12.9 R20.2," in exported.text and "99205" not in exported.text


async def test_every_export_records_its_snapshots_file_and_exporter_and_can_be_downloaded_again(harness, icd_catalog):
    practice, note_id = await _approved(harness, icd_catalog)
    [snapshot] = await _snapshots(note_id)

    exported = await harness.client.post("/api/billing/export", headers=practice.admin, json={})

    async with SessionFactory() as db:
        export = await db.scalar(select(ClaimExport))
        items = (await db.scalars(select(ClaimExportItem))).all()
    assert (export.format, export.again, export.notes_count, export.actor_role) == ("csv", False, 1, "admin")
    assert export.file_sha256 == hashlib.sha256(exported.content).hexdigest()
    assert harness.store.objects[export.file_key] == exported.content
    assert export.file_key == f"practices/{practice.id}/exports/{export.id}.csv"
    assert [(item.note_id, item.approved_claim_id, item.snapshot_revision) for item in items] == [
        (note_id, snapshot.id, 1)
    ]
    again = await harness.client.get(f"/api/billing/exports/{export.id}/file", headers=practice.admin)
    assert again.content == exported.content
    listing = (await harness.client.get("/api/billing/exports", headers=practice.admin)).json()
    assert [(row["id"], row["notes"], row["sha256"]) for row in listing["items"]] == [
        (export.id, 1, export.file_sha256)
    ]
    history = (await harness.client.get(f"/api/notes/{note_id}", headers=practice.admin)).json()["history"]
    assert [(row["id"], row["snapshot_revision"]) for row in history["exports"]] == [(export.id, 1)]


async def test_downloading_claim_lines_marks_the_visits_exported_and_records_the_file(harness, icd_catalog):
    practice, note_id = await _approved(harness, icd_catalog)

    lines = await harness.client.post("/api/billing/claim-lines", headers=practice.admin, json={"format": "csv"})

    assert lines.status_code == 200, lines.text
    async with SessionFactory() as db:
        export = await db.scalar(select(ClaimExport))
        note = await db.get_one(Note, note_id)
    assert (export.format, note.status) == ("claim_lines_csv", "exported")
    assert harness.store.objects[export.file_key] == lines.content
    again = await harness.client.post("/api/billing/claim-lines", headers=practice.admin, json={"format": "csv"})
    assert again.status_code == 422
    rows = (await harness.client.get("/api/access-log", headers=practice.admin)).json()["items"]
    assert any(row["action"] == "built claim lines" and export.id[:8] in row["detail"] for row in rows)
