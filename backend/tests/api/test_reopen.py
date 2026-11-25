from tests.builders import reviewed_note


async def test_an_approved_note_can_be_reopened_until_it_is_exported(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    path = f"/api/notes/{note_id}"
    assert (await harness.client.post(f"{path}/approve", headers=practice.admin)).status_code == 200

    reopened = await harness.client.post(f"{path}/reopen", headers=practice.admin)
    assert reopened.json() == {"status": "ready"}
    detail = (await harness.client.get(path, headers=practice.admin)).json()
    assert (detail["note"]["lane"], detail["note"]["lane_reason"]) == ("coder", "code_changes")
    assert [(c["kind"], c["revision"]) for c in detail["history"]["code_sets"]] == [("billed", 1), ("final", 1)]
    assert (await harness.client.get("/api/billing?show=ready", headers=practice.admin)).json()["items"] == []

    assert (await harness.client.post(f"{path}/approve", headers=practice.admin)).status_code == 200
    await harness.client.post("/api/billing/export", headers=practice.admin, json={})
    assert (await harness.client.post(f"{path}/reopen", headers=practice.admin)).status_code == 409
