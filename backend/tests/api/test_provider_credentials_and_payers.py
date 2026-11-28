from tests.builders import practice_with_provider

PROVIDER = {"name": "Amara Okafor", "credential": "DO", "email": "okafor@clinic.example.com"}
DETAILS = {
    "taxonomy_code": "207q00000x",
    "license_number": "do-778",
    "license_state": "tx",
    "dea_number": "BJ6125341",
    "bills_under": "group",
    "group_npi": "1234567893",
    "supervising_physician": "Elena Varga",
    "signature_on_file": True,
}
STORED = {
    **DETAILS,
    "taxonomy_code": "207Q00000X",
    "license_number": "DO-778",
    "license_state": "TX",
}
BLUE_CROSS = {"name": "Blue Cross Blue Shield of Texas", "payer_id": "g84980", "plan_type": "commercial"}


async def _details_of(harness, practice, name: str) -> dict:
    providers = (await harness.client.get("/api/providers", headers=practice.admin)).json()
    return next(provider["details"] for provider in providers if provider["name"] == name)


async def test_credentialing_details_are_checked_and_stored_with_the_provider(harness):
    practice = await practice_with_provider(harness)
    added = await harness.client.post("/api/providers", headers=practice.admin, json={**PROVIDER, "details": DETAILS})
    assert added.status_code == 200, added.text
    assert await _details_of(harness, practice, "Amara Okafor") == STORED

    kept = await harness.client.put(f"/api/providers/{added.json()['id']}", headers=practice.admin, json=PROVIDER)
    assert kept.status_code == 204
    assert await _details_of(harness, practice, "Amara Okafor") == STORED
    assert (await _details_of(harness, practice, "Elena Varga"))["signature_on_file"] is False


async def test_credentialing_details_that_cannot_be_right_are_refused(harness):
    practice = await practice_with_provider(harness)
    wrong = {
        "taxonomy_code": "207Q0000X",
        "dea_number": "BJ6125342",
        "group_npi": "1234567890",
        "license_state": "ZZ",
    }
    for field, value in wrong.items():
        details = {field: value, **({"license_number": "DO-778"} if field == "license_state" else {})}
        refused = await harness.client.post(
            "/api/providers", headers=practice.admin, json={**PROVIDER, "details": details}
        )
        assert refused.status_code == 422, field
        assert value in refused.json()["message"], field
    alone = await harness.client.post(
        "/api/providers", headers=practice.admin, json={**PROVIDER, "details": {"license_number": "DO-778"}}
    )
    assert alone.status_code == 422


async def test_imported_providers_carry_credentialing_columns(harness):
    practice = await practice_with_provider(harness)
    csv = (
        "name,credential,email,taxonomy_code,license_number,license_state,dea_number,bills_under,signature_on_file\n"
        "Amara Okafor,DO,okafor@clinic.example.com,207Q00000X,DO-778,TX,BJ6125341,Individual,yes\n"
    )
    imported = await harness.client.post("/api/providers/import", headers=practice.admin, json={"csv": csv})
    assert imported.json() == {"imported": 1}
    assert await _details_of(harness, practice, "Amara Okafor") == {
        **STORED,
        "bills_under": "individual",
        "group_npi": None,
        "supervising_physician": None,
    }
    bad = csv.replace(",yes\n", ",maybe\n")
    refused = await harness.client.post("/api/providers/import", headers=practice.admin, json={"csv": bad})
    assert refused.status_code == 422
    assert refused.json()["message"].startswith("row 2:")


async def test_payers_are_added_changed_and_removed_in_the_setup(harness):
    practice = await practice_with_provider(harness)
    added = await harness.client.post("/api/practice/payers", headers=practice.admin, json=BLUE_CROSS)
    assert added.status_code == 200, added.text
    payer_key = added.json()["id"]
    setup = (await harness.client.get("/api/practice/setup", headers=practice.admin)).json()
    assert setup["payers"] == [
        {"id": payer_key, **BLUE_CROSS, "payer_id": "G84980", "claim_filing": None, "active": True}
    ]
    assert setup["sections"]["payers"]["fields"] == ["clearinghouse", "eft_era_status"]
    assert setup["sections"]["payers"]["complete"] is False

    values = {"clearinghouse": "Availity", "eft_era_status": "Enrolled"}
    await harness.client.put("/api/practice/setup/payers", headers=practice.admin, json={"values": values})
    setup = (await harness.client.get("/api/practice/setup", headers=practice.admin)).json()
    assert (setup["sections"]["payers"]["complete"], len(setup["payers"])) == (True, 1)

    inactive = {**BLUE_CROSS, "active": False}
    changed = await harness.client.put(f"/api/practice/payers/{payer_key}", headers=practice.admin, json=inactive)
    assert changed.status_code == 204
    setup = (await harness.client.get("/api/practice/setup", headers=practice.admin)).json()
    assert (setup["sections"]["payers"]["complete"], setup["payers"][0]["active"]) == (False, False)

    removed = await harness.client.delete(f"/api/practice/payers/{payer_key}", headers=practice.admin)
    assert removed.status_code == 204
    assert (await harness.client.get("/api/practice/setup", headers=practice.admin)).json()["payers"] == []
    assert (await harness.client.delete(f"/api/practice/payers/{payer_key}", headers=practice.admin)).status_code == 404


async def test_a_payer_needs_a_unique_name_a_plan_type_and_a_real_payer_id(harness):
    practice = await practice_with_provider(harness)
    await harness.client.post("/api/practice/payers", headers=practice.admin, json=BLUE_CROSS)
    duplicate = {**BLUE_CROSS, "name": BLUE_CROSS["name"].upper()}
    assert (
        await harness.client.post("/api/practice/payers", headers=practice.admin, json=duplicate)
    ).status_code == 409
    for change in ({"plan_type": "tricare"}, {"payer_id": "0"}, {"name": ""}):
        payer = {**BLUE_CROSS, "name": "Medicare Part B", **change}
        assert (
            await harness.client.post("/api/practice/payers", headers=practice.admin, json=payer)
        ).status_code == 422
