from tests.builders import reviewed_note

WITH_SCREENINGS = "99215, 96127x2, I10, E11.9, N18.30"
CLAIM = ["99214", "96127 ×2", "E11.65", "N18.30", "I12.9", "R20.2"]


async def test_the_note_shows_billed_and_claim_estimates_of_the_medicare_national_amount(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)

    detail = (await harness.client.get(f"/api/notes/{note_id}", headers=practice.admin)).json()

    assert detail["estimate"] == {
        "release": "RVU26D",
        "setting": "non_facility",
        "billed": {"total": 192.39, "lines": [{"code": "99215", "amount": 192.39}], "unpriced": []},
        "claim": {"total": 135.61, "lines": [{"code": "99214", "amount": 135.61}], "unpriced": []},
        "difference": -56.78,
    }


async def test_units_flow_from_billed_codes_to_the_claim_billing_and_export(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)

    edited = await harness.client.put(
        f"/api/notes/{note_id}/billed-codes", headers=practice.admin, json={"codes": WITH_SCREENINGS}
    )
    assert edited.status_code == 200, edited.text
    detail = edited.json()
    assert detail["claim"] == CLAIM
    assert (detail["estimate"]["billed"]["total"], detail["estimate"]["claim"]["total"]) == (202.41, 145.63)
    assert detail["estimate"]["claim"]["lines"][1] == {"code": "96127 ×2", "amount": 10.02}

    await harness.client.post(f"/api/notes/{note_id}/approve", headers=practice.admin)
    row = (await harness.client.get("/api/billing", headers=practice.admin)).json()["items"][0]
    assert (row["codes"], row["estimate"], row["changed"]) == (CLAIM, 145.63, 7)

    export = await harness.client.post("/api/billing/export", headers=practice.admin, json={})
    assert ",99214 96127x2,E11.65 N18.30 I12.9 R20.2," in export.text


async def test_insights_show_the_estimated_difference_and_who_approved(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    await harness.client.post(f"/api/notes/{note_id}/approve", headers=practice.admin)

    insights = (await harness.client.get("/api/insights?days=7", headers=practice.admin)).json()

    assert insights["estimates"] == {
        "notes": 1,
        "difference": -56.78,
        "providers": [{"provider_name": "Elena Varga", "notes": 1, "difference": -56.78}],
    }
    [person] = insights["people"]
    assert (person["name"], person["approved"], person["changed"]) == ("Practice Admin", 1, 1)
    assert person["median_minutes"] >= 0
