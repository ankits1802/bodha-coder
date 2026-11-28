from tests.builders import adopt_signature, create_hq_user, invite_member, reviewed_note, sign_in

KEEP_REASON = "Risk of the chosen management was discussed with the patient at length"


async def _hq(harness) -> dict[str, str]:
    await create_hq_user()
    return await sign_in(harness.client, "hq@bodha.example.com")


async def test_a_place_of_service_without_a_care_setting_is_refused(harness):
    hq = await _hq(harness)
    response = await harness.client.put("/api/hq/places/99", headers=hq, json={"name": "Other", "active": True})
    assert response.status_code == 422
    assert "99" in response.json()["message"]


async def test_a_practice_needs_a_real_time_zone(harness):
    hq = await _hq(harness)
    response = await harness.client.post(
        "/api/hq/practices",
        headers=hq,
        json={
            "name": "Lakeside",
            "admin_name": "Practice Admin",
            "admin_email": "admin@lakeside.example.com",
            "plan": "professional",
            "seats": 5,
            "time_zone": "Mars/Olympus_Mons",
        },
    )
    assert response.status_code == 422


async def test_a_renewal_date_can_be_set_and_cleared(harness):
    hq = await _hq(harness)
    created = await harness.client.post(
        "/api/hq/practices",
        headers=hq,
        json={
            "name": "Lakeside",
            "admin_name": "Practice Admin",
            "admin_email": "admin@lakeside.example.com",
            "plan": "professional",
            "seats": 5,
            "time_zone": "America/New_York",
        },
    )
    path = f"/api/hq/practices/{created.json()['id']}"
    assert (await harness.client.patch(path, headers=hq, json={"renews_on": "2027-01-31"})).status_code == 204
    assert (await harness.client.patch(path, headers=hq, json={"seats": 6})).status_code == 204
    listed = (await harness.client.get("/api/hq/practices", headers=hq)).json()[0]
    assert (listed["renews_on"], listed["seats"], listed["time_zone"]) == ("2027-01-31", 6, "America/New_York")
    assert (await harness.client.patch(path, headers=hq, json={"renews_on": None})).status_code == 204
    assert (await harness.client.get("/api/hq/practices", headers=hq)).json()[0]["renews_on"] is None


async def test_a_flagged_note_shows_why_and_who_flagged_it(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    flagged = await harness.client.post(
        f"/api/notes/{note_id}/flag", headers=practice.admin, json={"reason": "Same exam text as last visit"}
    )
    assert flagged.status_code == 200, flagged.text
    row = (await harness.client.get("/api/compliance", headers=practice.admin)).json()["items"][0]
    assert (row["lane_reason"], row["flag_reason"], row["flagged_by_name"]) == (
        "flagged",
        "Same exam text as last visit",
        "Practice Admin",
    )
    assert (row["place_code"], row["visit_type"]) == ("11", "Established patient")


async def test_compliance_keeps_the_billed_level_with_its_reason_in_the_access_log(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    path = f"/api/notes/{note_id}"
    flagged = await harness.client.post(f"{path}/flag", headers=practice.admin, json={"reason": "Exam text copied"})
    assert flagged.status_code == 200, flagged.text
    await invite_member(harness, practice, name="Jordan Diaz", email="jordan@lakeside.example.com", role="compliance")
    compliance = await sign_in(harness.client, "jordan@lakeside.example.com", secret_box=practice.secrets)
    await adopt_signature(harness.client, compliance, name="Jordan Diaz")
    kept = await harness.client.post(
        f"{path}/compliance", headers=compliance, json={"decision": "keep", "reason": KEEP_REASON}
    )
    assert kept.status_code == 200, kept.text
    detail = (await harness.client.get(path, headers=practice.admin)).json()
    finals = [entry["reason"] for entry in detail["history"]["code_sets"] if entry["kind"] == "final"]
    assert (detail["note"]["status"], finals) == ("approved", ["compliance keep"])
    log = (await harness.client.get("/api/access-log", headers=practice.admin)).json()["items"]
    kept_entries = [(row["actor"], row["detail"]) for row in log if row["action"] == "compliance keep"]
    assert kept_entries == [("Jordan Diaz", KEEP_REASON)]


async def test_a_compliance_reason_longer_than_an_access_log_detail_is_refused(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    refused = await harness.client.post(
        f"/api/notes/{note_id}/compliance", headers=practice.admin, json={"decision": "keep", "reason": "x" * 301}
    )
    assert refused.status_code == 422


async def test_hq_reads_demo_requests_and_renames_a_practice(harness):
    sent = await harness.client.post(
        "/api/demo-requests",
        json={"name": "Dana Ortiz", "email": "dana@clinic.example.com", "organization": "Ortiz Family Medicine"},
    )
    assert sent.status_code == 204
    hq = await _hq(harness)
    rows = (await harness.client.get("/api/hq/demo-requests", headers=hq)).json()
    assert [(row["name"], row["organization"]) for row in rows] == [("Dana Ortiz", "Ortiz Family Medicine")]

    created = await harness.client.post(
        "/api/hq/practices",
        headers=hq,
        json={
            "name": "Lakeside",
            "admin_name": "Practice Admin",
            "admin_email": "admin@lakeside.example.com",
            "plan": "professional",
            "seats": 5,
        },
    )
    renamed = await harness.client.patch(
        f"/api/hq/practices/{created.json()['id']}", headers=hq, json={"name": "Lakeside Primary Care"}
    )
    assert renamed.status_code == 204
    assert (await harness.client.get("/api/hq/practices", headers=hq)).json()[0]["name"] == "Lakeside Primary Care"
    overview = (await harness.client.get("/api/hq/overview", headers=hq)).json()
    assert (overview["practices"], overview["people"]) == (1, 0)


async def test_a_note_waiting_for_compliance_cannot_be_approved_around_it(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    path = f"/api/notes/{note_id}"
    flagged = await harness.client.post(f"{path}/flag", headers=practice.admin, json={"reason": "Exam text copied"})
    assert flagged.status_code == 200, flagged.text
    await adopt_signature(harness.client, practice.admin)

    refused = await harness.client.post(f"{path}/approve", headers=practice.admin)

    assert refused.status_code == 409, refused.text
    assert "only compliance" in refused.json()["message"]
    detail = (await harness.client.get(path, headers=practice.admin)).json()
    assert (detail["note"]["status"], detail["note"]["lane"]) != ("approved", None)
