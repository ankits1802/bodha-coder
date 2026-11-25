from tests.builders import FILE_NAME, practice_with_provider, read_next_note, reviewed_note, upload_note


async def test_an_uploaded_note_is_read_and_waits_for_a_coder(harness, icd_catalog):
    practice = await practice_with_provider(harness)
    upload = await upload_note(harness, practice)
    assert upload.json()["accepted"] == [FILE_NAME]

    reviewer = await read_next_note(harness, icd_catalog)
    assert reviewer.calls[0].note_text is not None
    assert [code.code for code in reviewer.calls[0].billed_codes] == ["99215", "I10", "E11.9", "N18.30"]

    queue = (await harness.client.get("/api/notes?lane=coder", headers=practice.admin)).json()
    row = queue["items"][0]
    assert (row["patient_name"], row["headline"], row["billed"]) == (
        "Reyes Marisol",
        "Billed too high",
        ["99215", "I10", "E11.9", "N18.30"],
    )
    assert queue["lanes"]["coder"]["total"] == 1

    detail = (await harness.client.get(f"/api/notes/{row['id']}", headers=practice.admin)).json()
    assert detail["claim"] == ["99214", "E11.65", "N18.30", "I12.9", "R20.2"]
    assert [text["source"] for text in detail["texts"]] == ["document"]
    assert [(a["revision"], a["reason"], a["status"]) for a in detail["history"]["analyses"]] == [
        (1, "upload", "succeeded")
    ]
    assert any(key.endswith("/analyses/1.json") for key in harness.store.objects)


async def test_a_decided_note_is_approved_and_exported_once(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    decided = await harness.client.put(
        f"/api/notes/{note_id}/decisions", headers=practice.admin, json={"choices": {"dx:I10": "keep"}}
    )
    assert decided.json()["claim"] == ["99214", "I10", "E11.65", "N18.30", "I12.9", "R20.2"]
    assert decided.json()["history"]["decisions"][0]["key"] == "dx:I10"

    approved = await harness.client.post(f"/api/notes/{note_id}/approve", headers=practice.admin)
    assert approved.json() == {"status": "approved"}

    billing = (await harness.client.get("/api/billing", headers=practice.admin)).json()["items"]
    assert billing[0]["codes"] == ["99214", "I10", "E11.65", "N18.30", "I12.9", "R20.2"]

    export = await harness.client.post("/api/billing/export", headers=practice.admin, json={})
    assert export.headers["content-type"].startswith("text/csv")
    assert ",99214,I10 E11.65 N18.30 I12.9 R20.2," in export.text
    assert (await harness.client.get("/api/billing?show=ready", headers=practice.admin)).json()["items"] == []

    actions = [
        entry["action"] for entry in (await harness.client.get("/api/access-log", headers=practice.admin)).json()
    ]
    for action in ("uploaded notes", "opened note", "approved", "exported claims"):
        assert action in actions


async def test_the_same_pdf_is_not_uploaded_twice(harness):
    practice = await practice_with_provider(harness)
    await upload_note(harness, practice)
    again = await upload_note(harness, practice, file_name="copy.pdf")
    assert again.json()["duplicates"] == ["copy.pdf"]


async def test_editing_billed_codes_keeps_every_revision(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    edited = await harness.client.put(
        f"/api/notes/{note_id}/billed-codes",
        headers=practice.admin,
        json={"codes": "99214, I12.9, E11.65, N18.30, R20.2"},
    )
    history = edited.json()["history"]
    assert [(c["kind"], c["revision"]) for c in history["code_sets"]] == [("billed", 1), ("billed", 2)]
    assert [(a["revision"], a["status"]) for a in history["analyses"]] == [(1, "superseded"), (2, "succeeded")]
    assert edited.json()["note"]["headline"] == "1 question to send"


async def test_invalid_codes_are_refused_at_upload(harness):
    practice = await practice_with_provider(harness)
    response = await harness.client.post(
        "/api/uploads",
        headers=practice.admin,
        data={
            "provider_id": practice.provider_id,
            "service_date": "2026-11-25",
            "place_code": "11",
            "visit_type": "Established patient",
            "details": '[{"billed": "9921"}]',
        },
        files=[("files", ("note.pdf", b"%PDF-1.4 tiny", "application/pdf"))],
    )
    assert response.status_code == 422
    assert "9921" in response.json()["message"]
