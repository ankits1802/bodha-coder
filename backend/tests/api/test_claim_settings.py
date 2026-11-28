from tests.api.claim_helpers import PRACTICE_DETAILS, ok
from tests.builders import invite_member, practice_with_provider, sign_in

CHARGES = "/api/practice/charges"
DETAILS_FIELDS = [
    "legal_name",
    "tax_id",
    "group_npi",
    "taxonomy_code",
    "address",
    "address_line_2",
    "city",
    "state",
    "zip",
    "phone",
    "billing_contact",
]


async def test_an_admin_sets_imports_and_removes_charges(harness):
    practice = await practice_with_provider(harness)
    client, admin = harness.client, practice.admin

    assert ok(await client.put(f"{CHARGES}/99214", headers=admin, json={"cents": 15000})) == {
        "items": [{"code": "99214", "cents": 15000}]
    }
    imported = ok(
        await client.post(f"{CHARGES}/import", headers=admin, json={"csv": "code,charge\n96127,10.00\n99214,160\n"})
    )
    assert imported == {"items": [{"code": "96127", "cents": 1000}, {"code": "99214", "cents": 16000}]}
    assert ok(await client.delete(f"{CHARGES}/96127", headers=admin)) == {"items": [{"code": "99214", "cents": 16000}]}
    gone = await client.delete(f"{CHARGES}/96127", headers=admin)
    assert (gone.status_code, gone.json()["message"]) == (404, "96127 has no charge")
    bad = await client.put(f"{CHARGES}/ABC", headers=admin, json={"cents": 100})
    assert (bad.status_code, bad.json()["message"]) == (422, "ABC is not a CPT or HCPCS code")
    assert ok(await client.get(CHARGES, headers=admin)) == {"items": [{"code": "99214", "cents": 16000}]}


async def test_charges_are_for_admins_only(harness):
    practice = await practice_with_provider(harness)
    await invite_member(harness, practice, name="Bea Biller", email="biller@lakeside.example.com", role="biller")
    biller = await sign_in(harness.client, "biller@lakeside.example.com", secret_box=practice.secrets)

    assert (await harness.client.get(CHARGES, headers=biller)).status_code == 403
    assert (await harness.client.put(f"{CHARGES}/99214", headers=biller, json={"cents": 1})).status_code == 403


async def test_practice_details_are_structured_checked_and_complete_without_optional_fields(harness):
    practice = await practice_with_provider(harness)
    client, admin = harness.client, practice.admin

    bad = await client.put(
        "/api/practice/setup/practice_details", headers=admin, json={"values": {**PRACTICE_DETAILS, "zip": "6270"}}
    )
    assert (bad.status_code, bad.json()["message"]) == (422, "the ZIP code must be five digits or ZIP+4")
    values = {**PRACTICE_DETAILS, "taxonomy_code": "", "address_line_2": "", "state": "il"}
    ok(await client.put("/api/practice/setup/practice_details", headers=admin, json={"values": values}), 204)

    section = ok(await client.get("/api/practice/setup", headers=admin))["sections"]["practice_details"]
    assert section["fields"] == DETAILS_FIELDS
    assert section["optional"] == ["taxonomy_code", "address_line_2"]
    assert (section["complete"], section["values"]["state"]) == (True, "IL")


async def test_a_payer_carries_an_optional_claim_filing_code(harness):
    practice = await practice_with_provider(harness)
    client, admin = harness.client, practice.admin
    body = {"name": "Humana Gold", "payer_id": "61101", "plan_type": "medicare_advantage", "claim_filing": "HM"}

    ok(await client.post("/api/practice/payers", headers=admin, json=body))

    payers = ok(await client.get("/api/practice/setup", headers=admin))["payers"]
    assert [(payer["name"], payer["claim_filing"]) for payer in payers] == [("Humana Gold", "HM")]
    refused = await client.post(
        "/api/practice/payers", headers=admin, json={**body, "name": "Other", "claim_filing": "XX"}
    )
    assert refused.status_code == 422
