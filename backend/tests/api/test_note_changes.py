from tests.builders import reviewed_note


async def test_changing_the_visit_type_reads_the_note_again(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    changed = await harness.client.put(
        f"/api/notes/{note_id}/visit-type", headers=practice.admin, json={"visit_type": "New patient"}
    )
    assert changed.json() == {"status": "queued"}
    detail = (await harness.client.get(f"/api/notes/{note_id}", headers=practice.admin)).json()
    assert detail["note"]["visit_type"] == "New patient"
    assert detail["history"]["analyses"][-1]["reason"] == "visit_type"
    change = detail["history"]["changes"][-1]
    assert (change["field"], change["old"], change["new"], change["by"]) == (
        "visit_type",
        "Established patient",
        "New patient",
        "Practice Admin",
    )


async def test_cancelling_a_request_releases_the_held_claim(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    await harness.client.post(
        f"/api/notes/{note_id}/ask",
        headers=practice.admin,
        json={"questions": [{"key": "dx:N18.30", "text": "What stage?"}], "channel": "email", "hold": True},
    )
    cancelled = await harness.client.post(f"/api/notes/{note_id}/cancel-request", headers=practice.admin)
    assert cancelled.json() == {"lane": "coder"}
    detail = (await harness.client.get(f"/api/notes/{note_id}", headers=practice.admin)).json()
    assert detail["requests"][0]["status"] == "cancelled"
    assert (await harness.client.post(f"/api/notes/{note_id}/approve", headers=practice.admin)).status_code == 200


async def test_a_note_takes_one_of_the_practice_payers(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    added = await harness.client.post(
        "/api/practice/payers",
        headers=practice.admin,
        json={"name": "Medicare Part B", "payer_id": "00882", "plan_type": "medicare", "active": True},
    )
    assert added.status_code == 200, added.text
    payer_id = (await harness.client.get("/api/payers", headers=practice.admin)).json()[0]["id"]

    chosen = await harness.client.put(f"/api/notes/{note_id}/payer", headers=practice.admin, json={"payer": payer_id})
    assert chosen.json() == {"payer": payer_id}
    detail = (await harness.client.get(f"/api/notes/{note_id}", headers=practice.admin)).json()
    assert detail["note"]["payer"] == payer_id
    assert [(row["field"], row["old"], row["new"]) for row in detail["history"]["changes"]] == [
        ("payer", None, "Medicare Part B")
    ]
    cleared = await harness.client.put(f"/api/notes/{note_id}/payer", headers=practice.admin, json={"payer": None})
    assert cleared.json() == {"payer": None}
    again = (await harness.client.get(f"/api/notes/{note_id}", headers=practice.admin)).json()
    assert [(row["old"], row["new"]) for row in again["history"]["changes"]] == [
        (None, "Medicare Part B"),
        ("Medicare Part B", None),
    ]
    unknown = await harness.client.put(f"/api/notes/{note_id}/payer", headers=practice.admin, json={"payer": "nope"})
    assert unknown.status_code == 404
