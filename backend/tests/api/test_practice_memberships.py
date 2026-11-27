from tests.api.membership_helpers import (
    RIVERBEND_ADMIN,
    SAM,
    access_log,
    bearer,
    end_plan,
    me,
    membership_of,
    signed_in,
    switch,
    two_practices,
)
from tests.builders import PASSWORD, create_hq_user, practice_with_provider, sign_in, upload_note


async def test_one_person_holds_a_role_in_two_practices_and_switches_between_them(harness):
    both = await two_practices(harness)
    to, body = harness.messenger.sent[-1]
    assert to == SAM and "added to Riverbend" in body and "/sign-in" in body and "/set-password" not in body
    assert (await upload_note(harness, both.lakeside)).status_code == 200
    sam = await signed_in(harness, SAM)
    first = await me(harness, sam.headers)
    assert first["practice"]["name"] == "Lakeside"
    assert [(choice["name"], choice["role"]) for choice in first["practices"]] == [
        ("Lakeside", "coder"),
        ("Riverbend", "coder"),
    ]
    assert len((await harness.client.get("/api/notes", headers=sam.headers)).json()["items"]) == 1
    moved = await switch(harness, sam, both.riverbend.id)
    assert moved.status_code == 200, moved.text
    assert moved.json()["user"]["practice"]["name"] == "Riverbend"
    assert harness.client.cookies.get("bodha_refresh", domain="app.test", path="/api/auth") != sam.refresh
    riverbend = bearer(moved.json())
    assert (await harness.client.get("/api/notes", headers=riverbend)).json()["items"] == []
    refreshed = await harness.client.post("/api/auth/refresh")
    assert refreshed.json()["user"]["practice"]["name"] == "Riverbend"
    again = await harness.client.post("/api/auth/login", json={"email": SAM, "password": PASSWORD})
    assert again.json()["user"]["practice"]["name"] == "Riverbend"


async def test_the_switch_is_written_to_the_access_log_of_the_practice_entered(harness):
    both = await two_practices(harness)
    sam = await signed_in(harness, SAM)
    assert (await switch(harness, sam, both.riverbend.id)).status_code == 200
    riverbend_admin = await sign_in(harness.client, RIVERBEND_ADMIN, secret_box=both.riverbend.secrets)
    entries = [(row["actor"], row["action"]) for row in await access_log(harness, riverbend_admin)]
    assert ("Sam Patel", "practice switched") in entries
    lakeside_entries = [row["action"] for row in await access_log(harness, both.lakeside.admin)]
    assert "practice switched" not in lakeside_entries


async def test_switching_is_refused_for_a_practice_the_person_is_not_an_active_member_of(harness):
    lakeside = await practice_with_provider(harness)
    riverbend = await practice_with_provider(harness, name="Riverbend", admin_email=RIVERBEND_ADMIN)
    admin = await signed_in(harness, "admin@lakeside.example.com", lakeside.secrets)
    refused = await switch(harness, admin, riverbend.id)
    assert (refused.status_code, refused.json()["error"]) == (403, "forbidden")
    assert (await switch(harness, admin, "not-a-practice")).status_code == 403
    assert (await me(harness, admin.headers))["practice"]["name"] == "Lakeside"
    await create_hq_user()
    hq = await signed_in(harness, "hq@bodha.example.com", {})
    assert (await switch(harness, hq, riverbend.id)).status_code == 403


async def test_a_switch_needs_the_session_of_the_person_asking(harness):
    both = await two_practices(harness)
    sam = await signed_in(harness, SAM)
    admin = await signed_in(harness, "admin@lakeside.example.com", both.lakeside.secrets)
    harness.client.cookies.set("bodha_refresh", admin.refresh, domain="app.test", path="/api/auth")
    stolen = await harness.client.post(
        "/api/auth/practice", headers=sam.headers, json={"practice_id": both.riverbend.id}
    )
    assert stolen.status_code == 401


async def test_a_block_in_one_practice_leaves_the_person_their_other_practice(harness):
    both = await two_practices(harness)
    sam = await signed_in(harness, SAM)
    moved = bearer((await switch(harness, sam, both.riverbend.id)).json())
    riverbend_admin = await sign_in(harness.client, RIVERBEND_ADMIN, secret_box=both.riverbend.secrets)
    blocked = await harness.client.patch(f"/api/team/{both.sam_id}", headers=riverbend_admin, json={"blocked": True})
    assert blocked.status_code == 204
    assert (await harness.client.get("/api/notes", headers=moved)).status_code == 401
    back = await harness.client.post("/api/auth/login", json={"email": SAM, "password": PASSWORD})
    assert back.status_code == 200
    assert back.json()["user"]["practice"]["name"] == "Lakeside"
    assert [choice["name"] for choice in back.json()["user"]["practices"]] == ["Lakeside"]
    lakeside = await signed_in(harness, SAM)
    assert (await switch(harness, lakeside, both.riverbend.id)).status_code == 403


async def test_an_ended_plan_is_judged_per_practice_and_per_role(harness):
    both = await two_practices(harness)
    sam = await signed_in(harness, SAM)
    assert (await switch(harness, sam, both.riverbend.id)).status_code == 200
    await end_plan(both.riverbend.id)
    signed = await harness.client.post("/api/auth/login", json={"email": SAM, "password": PASSWORD})
    assert signed.json()["user"]["practice"]["name"] == "Lakeside"
    assert signed.json()["user"]["billing_only"] is False
    lakeside = await signed_in(harness, SAM)
    refused = await switch(harness, lakeside, both.riverbend.id)
    assert (refused.status_code, refused.json()["error"]) == (403, "plan_ended")
    riverbend_admin = await sign_in(harness.client, RIVERBEND_ADMIN, secret_box=both.riverbend.secrets)
    assert (await me(harness, riverbend_admin))["billing_only"] is True


async def test_a_role_belongs_to_the_practice_and_a_change_reaches_the_session(harness):
    both = await two_practices(harness, riverbend_role="viewer")
    sam = await signed_in(harness, SAM)
    assert (await harness.client.get("/api/notes", headers=sam.headers)).status_code == 200
    viewer = bearer((await switch(harness, sam, both.riverbend.id)).json())
    assert (await harness.client.get("/api/notes", headers=viewer)).status_code == 403
    riverbend_admin = await sign_in(harness.client, RIVERBEND_ADMIN, secret_box=both.riverbend.secrets)
    changed = await harness.client.patch(f"/api/team/{both.sam_id}", headers=riverbend_admin, json={"role": "coder"})
    assert changed.status_code == 204
    assert (await harness.client.get("/api/notes", headers=viewer)).status_code == 401
    assert (await membership_of(both.sam_id, both.lakeside.id)).role == "coder"
    entries = [row["action"] for row in await access_log(harness, riverbend_admin)]
    assert "member role changed" in entries


async def test_inviting_an_existing_account_adds_a_membership_and_logs_it(harness):
    both = await two_practices(harness)
    riverbend_admin = await sign_in(harness.client, RIVERBEND_ADMIN, secret_box=both.riverbend.secrets)
    entries = [(row["action"], row["detail"]) for row in await access_log(harness, riverbend_admin)]
    assert ("member added", "Sam Patel as coder") in entries
    membership = await membership_of(both.sam_id, both.riverbend.id)
    assert (membership.status, membership.ended_at) == ("active", None)
    again = await harness.client.post(
        "/api/team", headers=riverbend_admin, json={"name": "Sam", "email": SAM.upper(), "role": "viewer"}
    )
    assert (again.status_code, again.json()["message"]) == (409, "this person is already on the team")


async def test_a_new_email_gets_the_set_password_invite_and_accepting_is_logged(harness):
    practice = await practice_with_provider(harness)
    invited = await harness.client.post(
        "/api/team",
        headers=practice.admin,
        json={"name": "Ana Ruiz", "email": "ana@lakeside.example.com", "role": "biller"},
    )
    assert invited.status_code == 200
    to, body = harness.messenger.sent[-1]
    assert to == "ana@lakeside.example.com" and "/set-password#" in body
    assert (await membership_of(invited.json()["id"], practice.id)).status == "invited"
    token = harness.messenger.last_fragment()
    assert (
        await harness.client.post("/api/auth/password", json={"token": token, "password": PASSWORD})
    ).status_code == 204
    assert (await membership_of(invited.json()["id"], practice.id)).status == "active"
    entries = [(row["actor"], row["action"]) for row in await access_log(harness, practice.admin)]
    assert ("Practice Admin", "member invited") in entries and ("Ana Ruiz", "invite accepted") in entries


async def test_seats_count_live_memberships_of_each_practice_only(harness):
    both = await two_practices(harness)
    hq = await sign_in(harness.client, "hq-admin@riverbend.example.com", secret_box=both.riverbend.secrets)
    resized = await harness.client.patch(f"/api/hq/practices/{both.riverbend.id}", headers=hq, json={"seats": 2})
    assert resized.status_code == 204
    riverbend_admin = await sign_in(harness.client, RIVERBEND_ADMIN, secret_box=both.riverbend.secrets)
    ana = {"name": "Ana Ruiz", "email": "ana@riverbend.example.com", "role": "biller"}
    full = await harness.client.post("/api/team", headers=riverbend_admin, json=ana)
    assert (full.status_code, full.json()["message"]) == (409, "all seats are in use")
    assert (await harness.client.post("/api/team", headers=both.lakeside.admin, json=ana)).status_code == 200
    removed = await harness.client.delete(f"/api/team/{both.sam_id}", headers=riverbend_admin)
    assert removed.status_code == 204
    assert (await harness.client.post("/api/team", headers=riverbend_admin, json=ana)).status_code == 200
    team = (await harness.client.get("/api/team", headers=riverbend_admin)).json()["members"]
    assert sorted(member["email"] for member in team) == [RIVERBEND_ADMIN, "ana@riverbend.example.com"]


async def test_removing_a_member_ends_their_access_and_keeps_the_membership_record(harness):
    both = await two_practices(harness)
    sam = await signed_in(harness, SAM)
    riverbend_session = bearer((await switch(harness, sam, both.riverbend.id)).json())
    riverbend_admin = await sign_in(harness.client, RIVERBEND_ADMIN, secret_box=both.riverbend.secrets)
    assert (await harness.client.delete(f"/api/team/{both.sam_id}", headers=riverbend_admin)).status_code == 204
    assert (await harness.client.get("/api/notes", headers=riverbend_session)).status_code == 401
    ended = await membership_of(both.sam_id, both.riverbend.id)
    assert ended.ended_at is not None
    entries = [(row["action"], row["detail"]) for row in await access_log(harness, riverbend_admin)]
    assert ("member removed", "Sam Patel, coder") in entries
    readded = await harness.client.post(
        "/api/team", headers=riverbend_admin, json={"name": "Sam", "email": SAM, "role": "biller"}
    )
    assert readded.status_code == 200
    reopened = await membership_of(both.sam_id, both.riverbend.id)
    assert (reopened.id, reopened.role, reopened.ended_at) == (ended.id, "biller", None)


async def test_a_person_leaves_a_practice_from_their_account(harness):
    both = await two_practices(harness)
    sam = await signed_in(harness, SAM)
    left = await harness.client.post(f"/api/auth/practices/{both.riverbend.id}/leave", headers=sam.headers)
    assert left.status_code == 204
    assert [choice["name"] for choice in (await me(harness, sam.headers))["practices"]] == ["Lakeside"]
    assert (await membership_of(both.sam_id, both.riverbend.id)).ended_at is not None
    riverbend_admin = await sign_in(harness.client, RIVERBEND_ADMIN, secret_box=both.riverbend.secrets)
    entries = [(row["actor"], row["action"]) for row in await access_log(harness, riverbend_admin)]
    assert ("Sam Patel", "member left") in entries
    again = await harness.client.post(f"/api/auth/practices/{both.riverbend.id}/leave", headers=sam.headers)
    assert again.status_code == 404


async def test_the_last_active_admin_cannot_leave_and_an_invited_admin_does_not_count(harness):
    practice = await practice_with_provider(harness)
    invited = await harness.client.post(
        "/api/team",
        headers=practice.admin,
        json={"name": "Lee Park", "email": "lee@lakeside.example.com", "role": "admin"},
    )
    assert invited.status_code == 200
    refused = await harness.client.post(f"/api/auth/practices/{practice.id}/leave", headers=practice.admin)
    assert (refused.status_code, refused.json()["message"]) == (409, "a practice needs at least one active admin")
    token = harness.messenger.last_fragment()
    assert (
        await harness.client.post("/api/auth/password", json={"token": token, "password": PASSWORD})
    ).status_code == 204
    left = await harness.client.post(f"/api/auth/practices/{practice.id}/leave", headers=practice.admin)
    assert left.status_code == 204


async def test_an_admin_can_never_change_their_own_access(harness):
    practice = await practice_with_provider(harness)
    admin_id = (await me(harness, practice.admin))["id"]
    for change in ({"role": "coder"}, {"blocked": True}):
        refused = await harness.client.patch(f"/api/team/{admin_id}", headers=practice.admin, json=change)
        assert refused.status_code == 403
    assert (await harness.client.delete(f"/api/team/{admin_id}", headers=practice.admin)).status_code == 403


async def test_two_step_of_someone_in_two_practices_is_not_reset_by_one_practice(harness):
    both = await two_practices(harness)
    refused = await harness.client.post(f"/api/team/{both.sam_id}/reset-mfa", headers=both.lakeside.admin)
    assert refused.status_code == 409


async def test_an_admin_manages_memberships_only_in_their_own_practice(harness):
    both = await two_practices(harness)
    outsider = await practice_with_provider(harness, name="Harbor", admin_email="admin@harbor.example.com")
    for call in (
        harness.client.patch(f"/api/team/{both.sam_id}", headers=outsider.admin, json={"blocked": True}),
        harness.client.delete(f"/api/team/{both.sam_id}", headers=outsider.admin),
    ):
        assert (await call).status_code == 404
    assert (await membership_of(both.sam_id, both.lakeside.id)).status == "active"
