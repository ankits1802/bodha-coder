from tests.builders import create_hq_user, reviewed_note, sign_in


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
