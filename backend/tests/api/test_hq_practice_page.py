from tests.api.membership_helpers import SAM, two_practices
from tests.batches import add_provider
from tests.builders import Harness, Practice, accept_invite, practice_with_provider, sign_in, upload_note


async def hq_of(harness: Harness, practice: Practice) -> dict[str, str]:
    return await sign_in(harness.client, "hq-admin@lakeside.example.com", secret_box=practice.secrets)


async def invite(harness: Harness, practice: Practice, name: str, role: str) -> str:
    email = f"{name.split()[0].lower()}@lakeside.example.com"
    invited = await harness.client.post(
        "/api/team", headers=practice.admin, json={"name": name, "email": email, "role": role}
    )
    assert invited.status_code == 200, invited.text
    return invited.json()["id"]


async def test_hq_opens_one_practice_with_its_row_and_the_places_it_uses(harness):
    practice = await practice_with_provider(harness)
    await add_provider(harness, practice, name="Omar Haddad", specialty=None)
    assert (await upload_note(harness, practice)).status_code == 200
    hq = await hq_of(harness, practice)

    page = await harness.client.get(f"/api/hq/practices/{practice.id}", headers=hq)

    assert page.status_code == 200, page.text
    listed = (await harness.client.get("/api/hq/practices", headers=hq)).json()
    assert page.json()["practice"] == next(row for row in listed if row["id"] == practice.id)
    assert page.json()["places"] == [{"code": "11", "name": "Office", "active": True, "providers": 2, "notes": 1}]
    assert (await harness.client.get("/api/hq/practices/no-such-practice", headers=hq)).status_code == 404
    assert (await harness.client.get(f"/api/hq/practices/{practice.id}", headers=practice.admin)).status_code == 403


async def test_people_lists_live_members_with_role_status_two_step_and_last_active(harness):
    practice = await practice_with_provider(harness)
    await invite(harness, practice, "Cora Coder", "coder")
    await accept_invite(harness)
    await invite(harness, practice, "Ivy Invited", "biller")
    blocked = await invite(harness, practice, "Ben Blocked", "coder")
    await accept_invite(harness)
    removed = await invite(harness, practice, "Rita Removed", "cdi")
    await accept_invite(harness)
    assert (
        await harness.client.patch(f"/api/team/{blocked}", headers=practice.admin, json={"blocked": True})
    ).is_success
    assert (await harness.client.delete(f"/api/team/{removed}", headers=practice.admin)).status_code == 204
    hq = await hq_of(harness, practice)

    people = (await harness.client.get(f"/api/hq/practices/{practice.id}/people", headers=hq)).json()

    assert [(row["name"], row["role"], row["status"], row["mfa_enabled"]) for row in people] == [
        ("Ben Blocked", "coder", "blocked", False),
        ("Cora Coder", "coder", "active", False),
        ("Ivy Invited", "biller", "invited", False),
        ("Practice Admin", "admin", "active", True),
    ]
    assert [row["last_active_at"] is not None for row in people] == [False, False, False, True]
    assert people[3]["email"] == "admin@lakeside.example.com"
    missing = await harness.client.get("/api/hq/practices/no-such-practice/people", headers=hq)
    assert missing.status_code == 404


async def test_search_finds_practices_by_name_and_people_by_email_with_every_practice_they_belong_to(harness):
    pair = await two_practices(harness)
    hq = await hq_of(harness, pair.lakeside)

    by_name = (await harness.client.get("/api/hq/search", headers=hq, params={"q": "river"})).json()
    by_email = (await harness.client.get("/api/hq/search", headers=hq, params={"q": "sam@lake"})).json()

    assert [(row["id"], row["name"], row["status"]) for row in by_name["practices"]] == [
        (pair.riverbend.id, "Riverbend", "active")
    ]
    assert by_email["people"] == [
        {
            "id": pair.sam_id,
            "name": "Sam Patel",
            "email": SAM,
            "practices": [
                {"id": pair.lakeside.id, "name": "Lakeside", "role": "coder"},
                {"id": pair.riverbend.id, "name": "Riverbend", "role": "coder"},
            ],
        }
    ]
    assert (by_email["practices"], by_email["limit"]) == ([], 20)


async def test_search_escapes_wildcards_leaves_out_hq_accounts_and_is_for_hq_only(harness):
    practice = await practice_with_provider(harness)
    hq = await hq_of(harness, practice)

    wildcards = (await harness.client.get("/api/hq/search", headers=hq, params={"q": "%%"})).json()
    hq_accounts = (await harness.client.get("/api/hq/search", headers=hq, params={"q": "hq-admin"})).json()
    short = await harness.client.get("/api/hq/search", headers=hq, params={"q": "l"})
    practice_side = await harness.client.get("/api/hq/search", headers=practice.admin, params={"q": "lake"})

    assert (wildcards["practices"], wildcards["people"]) == ([], [])
    assert hq_accounts["people"] == []
    assert (short.status_code, practice_side.status_code) == (422, 403)
