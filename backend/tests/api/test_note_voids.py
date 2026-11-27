import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import DBAPIError

from app.core.config import get_settings
from app.core.db import SessionFactory
from app.models import Analysis, Note
from app.services.analysis import AnalysisDeps
from app.worker import process_one
from tests.builders import invite_member, practice_with_provider, reviewed_note, sign_in, upload_note
from tests.fakes import ScriptedReviewer

CODER = {"name": "Priya Nair", "email": "priya@lakeside.example.com", "role": "coder"}
MISTAKE = "uploaded to the wrong provider"


async def _void(harness, headers, note_ids, reason=MISTAKE):
    return await harness.client.post("/api/notes/void", headers=headers, json={"note_ids": note_ids, "reason": reason})


async def _queued_note(harness, practice) -> str:
    assert (await upload_note(harness, practice)).status_code == 200
    return (await harness.client.get("/api/notes", headers=practice.admin)).json()["items"][0]["id"]


async def test_a_coder_voids_an_unread_note_and_every_record_and_file_stays(harness, icd_catalog):
    practice = await practice_with_provider(harness)
    await invite_member(harness, practice, **CODER)
    coder = await sign_in(harness.client, CODER["email"])
    note_id = await _queued_note(harness, practice)
    files = {key for key in harness.store.objects if note_id in key}

    voided = await _void(harness, coder, [note_id])

    assert voided.json() == {"voided": [note_id]}
    assert (await harness.client.get("/api/notes", headers=practice.admin)).json()["items"] == []
    assert (await harness.client.get("/api/today", headers=practice.admin)).json()["batches"] == []
    assert {key for key in harness.store.objects if note_id in key} == files
    detail = (await harness.client.get(f"/api/notes/{note_id}", headers=practice.admin)).json()
    assert detail["note"]["status"] == "voided"
    assert {key: detail["note"]["voided"][key] for key in ("by", "reason", "was")} == {
        "by": "Priya Nair",
        "reason": MISTAKE,
        "was": "queued",
    }
    assert [(row["field"], row["old"], row["new"], row["reason"]) for row in detail["history"]["changes"]] == [
        ("status", "queued", "voided", MISTAKE)
    ]
    deps = AnalysisDeps(ScriptedReviewer(None), None, harness.store, icd_catalog)
    assert await process_one(deps, get_settings()) is False
    log = (await harness.client.get("/api/access-log", headers=practice.admin)).json()["items"]
    assert ("voided note", note_id, "was queued") in {(row["action"], row["note_id"], row["detail"]) for row in log}


async def test_a_coder_cannot_void_a_note_bodha_has_read(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    await invite_member(harness, practice, **CODER)
    coder = await sign_in(harness.client, CODER["email"])

    assert (await _void(harness, coder, [note_id])).status_code == 403
    assert (await harness.client.get(f"/api/notes/{note_id}", headers=practice.admin)).json()["note"]["status"] == (
        "ready"
    )


async def test_an_admin_voids_an_exported_note_and_restores_it(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    await harness.client.post(f"/api/notes/{note_id}/approve", headers=practice.admin)
    await harness.client.post("/api/billing/export", headers=practice.admin, json={})

    assert (await _void(harness, practice.admin, [note_id])).status_code == 200
    billing = (await harness.client.get("/api/billing", headers=practice.admin, params={"show": "all"})).json()
    assert billing["total"] == 0
    restored = await harness.client.post(
        f"/api/notes/{note_id}/restore", headers=practice.admin, json={"reason": "voided by mistake"}
    )

    assert restored.json() == {"status": "exported"}
    detail = (await harness.client.get(f"/api/notes/{note_id}", headers=practice.admin)).json()
    assert detail["note"]["voided"] is None
    assert [(row["old"], row["new"], row["reason"]) for row in detail["history"]["changes"]] == [
        ("exported", "voided", MISTAKE),
        ("voided", "exported", "voided by mistake"),
    ]


async def test_only_an_admin_restores_a_voided_note(harness, icd_catalog):
    practice = await practice_with_provider(harness)
    await invite_member(harness, practice, **CODER)
    coder = await sign_in(harness.client, CODER["email"])
    note_id = await _queued_note(harness, practice)
    await _void(harness, coder, [note_id])

    refused = await harness.client.post(f"/api/notes/{note_id}/restore", headers=coder, json={"reason": "oops"})
    assert refused.status_code == 403
    restored = await harness.client.post(
        f"/api/notes/{note_id}/restore", headers=practice.admin, json={"reason": "oops"}
    )
    assert restored.json() == {"status": "queued"}
    async with SessionFactory() as db:
        statuses = (await db.scalars(select(Analysis.status).where(Analysis.note_id == note_id))).all()
    assert sorted(statuses) == ["queued", "superseded"]


async def test_voiding_needs_a_reason(harness, icd_catalog):
    practice = await practice_with_provider(harness)
    note_id = await _queued_note(harness, practice)
    assert (await _void(harness, practice.admin, [note_id], reason="  ")).status_code == 422
    assert (await _void(harness, practice.admin, [note_id], reason="no")).status_code == 422


async def test_a_note_with_an_open_provider_request_is_not_voided(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    await harness.client.post(
        f"/api/notes/{note_id}/ask",
        headers=practice.admin,
        json={"questions": [{"key": "dx:N18.30", "text": "What stage?"}], "channel": "email", "hold": True},
    )
    assert (await _void(harness, practice.admin, [note_id])).status_code == 409


async def test_a_voided_pdf_can_be_uploaded_again_and_then_the_void_stands(harness, icd_catalog):
    practice = await practice_with_provider(harness)
    note_id = await _queued_note(harness, practice)
    await _void(harness, practice.admin, [note_id])

    again = await upload_note(harness, practice)

    assert again.status_code == 200, again.text
    listed = (await harness.client.get("/api/notes", headers=practice.admin)).json()["items"]
    assert [row["id"] for row in listed] != [note_id] and len(listed) == 1
    restored = await harness.client.post(
        f"/api/notes/{note_id}/restore", headers=practice.admin, json={"reason": "x y"}
    )
    assert restored.status_code == 409


async def test_a_voided_note_is_not_edited(harness, icd_catalog):
    practice = await practice_with_provider(harness)
    note_id = await _queued_note(harness, practice)
    await _void(harness, practice.admin, [note_id])

    payer = await harness.client.put(f"/api/notes/{note_id}/payer", headers=practice.admin, json={"payer": None})
    visit = await harness.client.put(
        f"/api/notes/{note_id}/visit-type", headers=practice.admin, json={"visit_type": "New patient"}
    )
    assert (payer.status_code, visit.status_code) == (409, 409)
    assert (await _void(harness, practice.admin, [note_id])).status_code == 409


async def test_the_database_refuses_to_delete_a_note(harness, icd_catalog):
    practice = await practice_with_provider(harness)
    note_id = await _queued_note(harness, practice)
    async with SessionFactory() as db:
        with pytest.raises(DBAPIError, match="refused"):
            await db.execute(delete(Note).where(Note.id == note_id))
