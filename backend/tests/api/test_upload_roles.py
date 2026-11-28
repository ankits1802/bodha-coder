import json

import pytest

from tests.builders import BILLED, invite_member, practice_with_provider, sign_in
from tests.fakes import NOTE_TEXT, text_pdf

PEOPLE = {
    "viewer": "vic@lakeside.example.com",
    "biller": "bea@lakeside.example.com",
    "cdi": "cal@lakeside.example.com",
    "compliance": "cora@lakeside.example.com",
}


@pytest.mark.parametrize("role", sorted(PEOPLE))
async def test_every_practice_role_uploads_notes_and_reads_the_upload_history(harness, role):
    practice = await practice_with_provider(harness)
    email = PEOPLE[role]
    await invite_member(harness, practice, name=f"{role.title()} Person", email=email, role=role)
    person = await sign_in(harness.client, email, secret_box=practice.secrets)
    form = {
        "provider_id": practice.provider_id,
        "service_date": "2026-11-25",
        "place_code": "11",
        "visit_type": "Established patient",
        "details": json.dumps([{"billed": BILLED}]),
    }
    files = [("files", (f"{role}-note.pdf", text_pdf(f"{NOTE_TEXT} {role}"), "application/pdf"))]

    uploaded = await harness.client.post("/api/uploads", headers=person, data=form, files=files)
    history = await harness.client.get("/api/batches", headers=person)

    assert uploaded.status_code == 200, uploaded.text
    assert len(uploaded.json()["accepted"]) == 1
    assert history.status_code == 200, history.text
    assert history.json()["total"] == 1


async def test_voiding_notes_stays_with_admins_and_coders(harness):
    practice = await practice_with_provider(harness)
    await invite_member(harness, practice, name="Vic Viewer", email=PEOPLE["viewer"], role="viewer")
    viewer = await sign_in(harness.client, PEOPLE["viewer"], secret_box=practice.secrets)
    body = {"note_ids": ["n1"], "reason": "Uploaded twice"}
    refused = await harness.client.post("/api/notes/void", headers=viewer, json=body)
    assert refused.status_code == 403
