from tests.builders import (
    FILE_NAME,
    create_hq_user,
    new_practice,
    practice_with_provider,
    read_next_note,
    sign_in,
    upload_note,
)
from tests.fakes import NOTE_TEXT

EARLIER_FILE = "2026-11-24 - CHEN LI - 99213 - Progress.pdf"


async def test_upload_history_lists_batches_newest_first_with_counts(harness):
    practice = await practice_with_provider(harness)
    first = await upload_note(harness, practice, file_name=EARLIER_FILE, body="Earlier visit. " + NOTE_TEXT)
    second = await upload_note(harness, practice)
    repeat = await upload_note(harness, practice)
    assert repeat.json()["duplicates"] == [FILE_NAME]

    page = (await harness.client.get("/api/batches", headers=practice.admin)).json()
    assert (page["total"], page["offset"], page["page_size"]) == (2, 0, 50)
    assert [item["id"] for item in page["items"]] == [second.json()["batch_id"], first.json()["batch_id"]]
    newest = page["items"][0]
    assert {key: newest[key] for key in ("provider_name", "service_date", "place_code", "uploaded_by", "counts")} == {
        "provider_name": "Elena Varga",
        "service_date": "2026-11-25",
        "place_code": "11",
        "uploaded_by": "Practice Admin",
        "counts": {"queued": 1},
    }
    later = (await harness.client.get("/api/batches", headers=practice.admin, params={"offset": 1})).json()
    assert (later["total"], [item["id"] for item in later["items"]]) == (2, [first.json()["batch_id"]])
    assert (await harness.client.get("/api/batches?offset=-1", headers=practice.admin)).status_code == 422


async def test_billing_pages_hold_the_offset_and_the_total(harness, icd_catalog):
    practice = await practice_with_provider(harness)
    for name, body in ((EARLIER_FILE, "Earlier visit. " + NOTE_TEXT), (FILE_NAME, NOTE_TEXT)):
        assert (await upload_note(harness, practice, file_name=name, body=body)).status_code == 200
        await read_next_note(harness, icd_catalog)
    for note in (await harness.client.get("/api/notes", headers=practice.admin)).json()["items"]:
        approved = await harness.client.post(f"/api/notes/{note['id']}/approve", headers=practice.admin)
        assert approved.status_code == 200, approved.text

    page = (await harness.client.get("/api/billing", headers=practice.admin)).json()
    assert (page["total"], page["offset"], page["page_size"], page["limit"], len(page["items"])) == (2, 0, 100, 500, 2)
    rest = (await harness.client.get("/api/billing", headers=practice.admin, params={"offset": 1})).json()
    assert (rest["total"], [row["id"] for row in rest["items"]]) == (2, [page["items"][1]["id"]])


async def test_the_access_log_pages_by_offset_with_a_total(harness):
    practice = await practice_with_provider(harness)
    full = (await harness.client.get("/api/access-log", headers=practice.admin)).json()
    assert (full["offset"], full["page_size"]) == (0, 200)
    assert full["total"] == len(full["items"]) >= 1
    rest = (await harness.client.get("/api/access-log", headers=practice.admin, params={"offset": 1})).json()
    assert (rest["total"], rest["items"]) == (full["total"], full["items"][1:])


async def test_hq_activity_filters_by_practice_and_action_on_the_server(harness):
    await create_hq_user()
    hq = await sign_in(harness.client, "hq@bodha.example.com")
    lakeside = await new_practice(harness, name="Lakeside", admin_email="admin@lakeside.example.com", hq_headers=hq)
    harbor = await new_practice(harness, name="Harbor", admin_email="admin@harbor.example.com", hq_headers=hq)
    await harness.client.patch(f"/api/hq/practices/{lakeside}", headers=hq, json={"seats": 12})

    updated = (await harness.client.get("/api/hq/activity", headers=hq, params={"action": "practice updated"})).json()
    assert updated["total"] == 1
    assert [(item["action"], item["practice_id"]) for item in updated["items"]] == [("practice updated", lakeside)]
    assert {"practice added", "practice updated"} <= set(updated["actions"])

    by_harbor = (await harness.client.get("/api/hq/activity", headers=hq, params={"practice_id": harbor})).json()
    assert {item["practice_id"] for item in by_harbor["items"]} == {harbor}
    assert "practice added" in [item["action"] for item in by_harbor["items"]]
    assert by_harbor["total"] == len(by_harbor["items"])

    lakeside_page = {"practice_id": lakeside}
    full = (await harness.client.get("/api/hq/activity", headers=hq, params=lakeside_page)).json()
    rest = (await harness.client.get("/api/hq/activity", headers=hq, params={**lakeside_page, "offset": 1})).json()
    assert (rest["total"], rest["items"]) == (full["total"], full["items"][1:])
