from tests.builders import create_hq_user, invite_member, new_practice, reviewed_note, sign_in

FLAG = "Exam text copied from the last visit"
RETURN = "The exam was repeated and documented"
CODER = {"name": "Priya Nair", "email": "priya@lakeside.example.com", "role": "coder"}


def _changes(detail: dict) -> list[tuple]:
    return [(row["field"], row["old"], row["new"], row["reason"], row["by"]) for row in detail["history"]["changes"]]


async def test_a_flag_and_its_return_by_compliance_are_kept_with_old_and_new_values(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    path = f"/api/notes/{note_id}"
    assert (await harness.client.post(f"{path}/flag", headers=practice.admin, json={"reason": FLAG})).status_code == 200
    await invite_member(harness, practice, name="Jordan Diaz", email="jordan@lakeside.example.com", role="compliance")
    compliance = await sign_in(harness.client, "jordan@lakeside.example.com", secret_box=practice.secrets)

    returned = await harness.client.post(
        f"{path}/compliance", headers=compliance, json={"decision": "return", "reason": RETURN}
    )

    assert returned.status_code == 200, returned.text
    detail = (await harness.client.get(path, headers=practice.admin)).json()
    assert _changes(detail) == [
        ("flag", None, FLAG, None, "Practice Admin"),
        ("flag", FLAG, None, RETURN, "Jordan Diaz"),
    ]


async def test_each_assignment_keeps_who_had_the_note_before(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    coder_id = await invite_member(harness, practice, **CODER)
    for user_id in (coder_id, None):
        assigned = await harness.client.post(
            "/api/notes/assign", headers=practice.admin, json={"note_ids": [note_id], "user_id": user_id}
        )
        assert assigned.status_code == 200, assigned.text

    detail = (await harness.client.get(f"/api/notes/{note_id}", headers=practice.admin)).json()
    assert [(row["field"], row["old"], row["new"]) for row in detail["history"]["changes"]] == [
        ("assignee", None, "Priya Nair"),
        ("assignee", "Priya Nair", None),
    ]


async def test_an_hq_practice_update_keeps_every_changed_value_before_and_after(harness):
    await create_hq_user()
    hq = await sign_in(harness.client, "hq@bodha.example.com")
    practice_id = await new_practice(harness, name="Lakeside", admin_email="admin@lakeside.example.com", hq_headers=hq)
    path = f"/api/hq/practices/{practice_id}"
    changes = {"name": "Lakeside Clinic", "seats": 12, "time_zone": "America/New_York", "renews_on": "2027-03-31"}

    assert (await harness.client.patch(path, headers=hq, json=changes)).status_code == 204
    assert (await harness.client.patch(path, headers=hq, json={"status": "blocked"})).status_code == 204

    updates = (await harness.client.get("/api/hq/activity", headers=hq, params={"action": "practice updated"})).json()
    blocked, edited = updates["items"]
    assert sorted((row["field"], row["before"], row["after"]) for row in edited["changes"]) == [
        ("name", "Lakeside", "Lakeside Clinic"),
        ("renews_on", None, "2027-03-31"),
        ("seats", 10, 12),
        ("time_zone", "America/Chicago", "America/New_York"),
    ]
    assert blocked["changes"] == [{"field": "status", "before": "active", "after": "blocked"}]
