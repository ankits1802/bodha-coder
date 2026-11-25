from tests.builders import PASSWORD, accept_invite, practice_with_provider, reviewed_note, sign_in, upload_note


async def test_a_wrong_password_and_an_unknown_email_get_the_same_answer(harness):
    await practice_with_provider(harness)
    wrong = await harness.client.post(
        "/api/auth/login", json={"email": "admin@lakeside.example.com", "password": "nope-nope-nope"}
    )
    unknown = await harness.client.post(
        "/api/auth/login", json={"email": "nobody@lakeside.example.com", "password": PASSWORD}
    )
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json()["message"] == unknown.json()["message"]


async def test_admins_must_pass_two_step_verification(harness):
    await practice_with_provider(harness)
    response = await harness.client.post(
        "/api/auth/login", json={"email": "admin@lakeside.example.com", "password": PASSWORD}
    )
    assert response.json()["mfa"] == "verify"
    assert "access_token" not in response.json()


async def test_a_refresh_token_works_once(harness):
    await practice_with_provider(harness)
    used = harness.client.cookies.get("bodha_refresh", domain="app.test", path="/api/auth")
    assert (await harness.client.post("/api/auth/refresh")).status_code == 200
    harness.client.cookies.clear()
    harness.client.cookies.set("bodha_refresh", used, domain="app.test", path="/api/auth")
    replay = await harness.client.post("/api/auth/refresh")
    assert replay.status_code == 401


async def test_another_practice_cannot_see_a_note(harness, icd_catalog):
    _, note_id = await reviewed_note(harness, icd_catalog)
    other = await practice_with_provider(harness, name="Riverbend", admin_email="admin@riverbend.example.com")
    response = await harness.client.get(f"/api/notes/{note_id}", headers=other.admin)
    assert response.status_code == 404


async def test_a_viewer_sees_today_but_no_patient_notes(harness, icd_catalog):
    practice, _ = await reviewed_note(harness, icd_catalog)
    invited = await harness.client.post(
        "/api/team",
        headers=practice.admin,
        json={"name": "Tom Reyes", "email": "tom@lakeside.example.com", "role": "viewer"},
    )
    assert invited.status_code == 200, invited.text
    await accept_invite(harness)
    viewer = await sign_in(harness.client, "tom@lakeside.example.com")
    today = await harness.client.get("/api/today", headers=viewer)
    assert today.status_code == 200 and today.json()["next_up"] == []
    assert (await harness.client.get("/api/notes", headers=viewer)).status_code == 403


async def test_blocking_a_member_ends_their_session_at_once(harness):
    practice = await practice_with_provider(harness)
    invited = await harness.client.post(
        "/api/team",
        headers=practice.admin,
        json={"name": "Sam Patel", "email": "sam@lakeside.example.com", "role": "coder"},
    )
    await accept_invite(harness)
    coder = await sign_in(harness.client, "sam@lakeside.example.com")
    assert (await upload_note(harness, practice)).status_code == 200
    blocked = await harness.client.patch(
        f"/api/team/{invited.json()['id']}", headers=practice.admin, json={"blocked": True}
    )
    assert blocked.status_code == 204
    assert (await harness.client.get("/api/notes", headers=coder)).status_code == 401


async def test_a_malformed_request_gets_a_plain_message_without_the_input(harness):
    response = await harness.client.post("/api/auth/login", json={"email": "not-an-email", "password": "x"})
    assert response.status_code == 422
    assert response.json()["error"] == "invalid"
    assert response.json()["message"].startswith("email: ")
    assert "not-an-email" not in response.text
