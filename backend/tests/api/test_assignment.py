from tests.builders import invite_member, practice_with_provider, reviewed_note, sign_in

CODER = {"name": "Priya Nair", "email": "priya@lakeside.example.com", "role": "coder"}


async def _assign(harness, headers, note_ids, user_id):
    return await harness.client.post(
        "/api/notes/assign", headers=headers, json={"note_ids": note_ids, "user_id": user_id}
    )


async def _queue_ids(harness, headers, **params) -> list[str]:
    listing = await harness.client.get("/api/notes", headers=headers, params=params)
    assert listing.status_code == 200, listing.text
    return [row["id"] for row in listing.json()["items"]]


async def _my_id(harness, headers) -> str:
    return (await harness.client.get("/api/auth/me", headers=headers)).json()["id"]


async def test_an_admin_assigns_a_note_and_the_queue_shows_who_has_it(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    coder_id = await invite_member(harness, practice, **CODER)
    coder = await sign_in(harness.client, CODER["email"])

    assigned = await _assign(harness, practice.admin, [note_id], coder_id)
    assert assigned.json() == {"assigned": [note_id]}

    row = (await harness.client.get("/api/notes", headers=practice.admin)).json()["items"][0]
    assert (row["assigned_to"], row["assignee_name"]) == (coder_id, "Priya Nair")
    assert await _queue_ids(harness, coder, assigned="me") == [note_id]
    assert await _queue_ids(harness, practice.admin, assigned=coder_id) == [note_id]
    assert await _queue_ids(harness, practice.admin, assigned="me") == []
    assert await _queue_ids(harness, practice.admin, assigned="none") == []

    detail = (await harness.client.get(f"/api/notes/{note_id}", headers=coder)).json()
    assert (detail["note"]["assigned_to"], detail["note"]["assignee_name"]) == (coder_id, "Priya Nair")
    log = (await harness.client.get("/api/access-log", headers=practice.admin)).json()["items"]
    assert {(entry["action"], entry["note_id"], entry["detail"]) for entry in log} >= {
        ("assigned", note_id, "to Priya Nair")
    }


async def test_a_coder_takes_and_releases_only_their_own_notes(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    coder_id = await invite_member(harness, practice, **CODER)
    coder = await sign_in(harness.client, CODER["email"])
    admin_id = await _my_id(harness, practice.admin)

    assert (await _assign(harness, coder, [note_id], admin_id)).status_code == 403
    assert (await _assign(harness, coder, [note_id], coder_id)).status_code == 200
    assert await _queue_ids(harness, coder, assigned="me") == [note_id]
    assert (await _assign(harness, coder, [note_id], None)).status_code == 200
    assert await _queue_ids(harness, coder, assigned="none") == [note_id]

    assert (await _assign(harness, practice.admin, [note_id], admin_id)).status_code == 200
    assert (await _assign(harness, coder, [note_id], coder_id)).status_code == 403
    assert (await _assign(harness, coder, [note_id], None)).status_code == 403
    assert await _queue_ids(harness, practice.admin, assigned="me") == [note_id]


async def test_only_active_note_readers_of_the_same_practice_can_be_assigned(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    viewer_id = await invite_member(
        harness, practice, name="Sam Okafor", email="sam@lakeside.example.com", role="viewer"
    )
    biller_id = await invite_member(harness, practice, name="Ana Ruiz", email="ana@lakeside.example.com", role="biller")
    biller = await sign_in(harness.client, "ana@lakeside.example.com")
    hillside = await practice_with_provider(harness, name="Hillside", admin_email="admin@hillside.example.com")
    hillside_admin_id = await _my_id(harness, hillside.admin)

    assert (await _assign(harness, practice.admin, [note_id], viewer_id)).status_code == 422
    assert (await _assign(harness, practice.admin, [note_id], hillside_admin_id)).status_code == 404
    assert (await _assign(harness, hillside.admin, [note_id], hillside_admin_id)).status_code == 404
    assert (await _assign(harness, biller, [note_id], biller_id)).status_code == 403
    assert (await _assign(harness, practice.admin, [note_id], biller_id)).status_code == 200


async def test_approving_keeps_the_assignment(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    admin_id = await _my_id(harness, practice.admin)
    assert (await _assign(harness, practice.admin, [note_id], admin_id)).status_code == 200
    await harness.client.put(
        f"/api/notes/{note_id}/decisions", headers=practice.admin, json={"choices": {"dx:I10": "keep"}}
    )

    approved = await harness.client.post(f"/api/notes/{note_id}/approve", headers=practice.admin)
    assert approved.json() == {"status": "approved"}
    detail = (await harness.client.get(f"/api/notes/{note_id}", headers=practice.admin)).json()
    assert (detail["note"]["status"], detail["note"]["assigned_to"]) == ("approved", admin_id)
    assert (await _assign(harness, practice.admin, [note_id], None)).status_code == 409
