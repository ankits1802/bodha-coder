from tests.builders import DOCUMENTED, invite_member, practice_with_provider, reviewed_note, sign_in


async def _found(harness, headers, text: str) -> list[str]:
    response = await harness.client.get("/api/search", headers=headers, params={"q": text})
    assert response.status_code == 200, response.text
    return [item["id"] for item in response.json()["items"]]


async def test_search_finds_a_note_by_patient_provider_file_and_billed_code(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    for text in ("mariSOL", "varga", "REYES MARISOL - 99215", "99215", "e11.9", "E119", "n18.30"):
        assert await _found(harness, practice.admin, text) == [note_id], text
    for text in ("99213", "%%", "__", "Okafor"):
        assert await _found(harness, practice.admin, text) == [], text


async def test_search_reaches_approved_notes_and_their_final_codes(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    assert await _found(harness, practice.admin, "99214") == []
    await harness.client.put(
        f"/api/notes/{note_id}/decisions",
        headers=practice.admin,
        json={"choices": {"dx:I10": "keep"}, "reasons": {"dx:I10": DOCUMENTED}},
    )
    assert (await harness.client.post(f"/api/notes/{note_id}/approve", headers=practice.admin)).status_code == 200

    response = await harness.client.get("/api/search", headers=practice.admin, params={"q": "99214"})
    assert [(item["id"], item["status"]) for item in response.json()["items"]] == [(note_id, "approved")]


async def test_search_stays_in_the_practice_and_logs_only_the_count(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    hillside = await practice_with_provider(harness, name="Hillside", admin_email="admin@hillside.example.com")
    assert await _found(harness, hillside.admin, "marisol") == []
    assert await _found(harness, practice.admin, "marisol") == [note_id]

    log = (await harness.client.get("/api/access-log", headers=practice.admin)).json()["items"]
    searched = [entry["detail"] for entry in log if entry["action"] == "searched"]
    assert searched == ["1 results"]


async def test_search_needs_two_characters_and_a_note_reading_role(harness, icd_catalog):
    practice, _ = await reviewed_note(harness, icd_catalog)
    await invite_member(harness, practice, name="Sam Okafor", email="sam@lakeside.example.com", role="viewer")
    viewer = await sign_in(harness.client, "sam@lakeside.example.com")

    short = await harness.client.get("/api/search", headers=practice.admin, params={"q": " m "})
    assert short.status_code == 422
    assert (await harness.client.get("/api/search", headers=viewer, params={"q": "marisol"})).status_code == 403
