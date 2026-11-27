from tests.api.membership_helpers import access_log
from tests.api.organization_helpers import DOMAIN, claim_rows, organization_of_two, organization_path
from tests.builders import invite_member, practice_with_provider, sign_in

DOMAINS = "/api/practice/domains"


async def _claim(harness, admin, domain: str = DOMAIN) -> str:
    claimed = await harness.client.post(DOMAINS, headers=admin, json={"domain": domain})
    assert claimed.status_code == 200, claimed.text
    return claimed.json()["id"]


async def _listed(harness, admin) -> dict[str, dict]:
    return {row["id"]: row for row in (await harness.client.get(DOMAINS, headers=admin)).json()}


async def test_public_email_services_and_their_subdomains_can_never_be_claimed(harness):
    practice = await practice_with_provider(harness)

    refused = [
        await harness.client.post(DOMAINS, headers=practice.admin, json={"domain": domain})
        for domain in ("gmail.com", "Outlook.com", "mail.yahoo.com", "not a domain")
    ]

    assert [response.status_code for response in refused] == [422, 422, 422, 422]
    assert refused[0].json()["message"] == "public email services such as gmail.com cannot be claimed"
    assert await claim_rows("gmail.com") == []


async def test_a_domain_is_verified_only_when_its_txt_record_carries_the_claim_token(harness):
    practice = await practice_with_provider(harness)
    claim_id = await _claim(harness, practice.admin, "@Lakeside.Example.com.")
    record = (await _listed(harness, practice.admin))[claim_id]
    assert (record["domain"], record["verified"]) == (DOMAIN, False)
    assert record["txt_record"].startswith("bodha-verify=")

    harness.dns.records[DOMAIN] = ["v=spf1 -all", "bodha-verify=someone-else"]
    missing = await harness.client.post(f"{DOMAINS}/{claim_id}/check", headers=practice.admin)
    harness.dns.records[DOMAIN].append(f" {record['txt_record']} ")
    found = await harness.client.post(f"{DOMAINS}/{claim_id}/check", headers=practice.admin)

    assert missing.status_code == 409 and record["txt_record"] in missing.json()["message"]
    assert found.status_code == 204, found.text
    verified = (await _listed(harness, practice.admin))[claim_id]
    assert (verified["verified"], verified["verified_via"], verified["txt_record"]) == (True, "dns", None)
    actions = [entry["action"] for entry in await access_log(harness, practice.admin)]
    assert "domain claimed" in actions and "domain verified" in actions
    assert harness.dns.lookups == [DOMAIN, DOMAIN]


async def test_only_one_practice_can_hold_a_verified_domain(harness):
    lakeside = await practice_with_provider(harness)
    riverbend = await practice_with_provider(harness, name="Riverbend", admin_email="admin@riverbend.example.com")
    first = await _claim(harness, lakeside.admin)
    second = await _claim(harness, riverbend.admin)
    tokens = [
        (await _listed(harness, admin))[claim]["txt_record"]
        for admin, claim in ((lakeside.admin, first), (riverbend.admin, second))
    ]
    harness.dns.records[DOMAIN] = tokens

    assert (await harness.client.post(f"{DOMAINS}/{first}/check", headers=lakeside.admin)).status_code == 204
    taken = await harness.client.post(f"{DOMAINS}/{second}/check", headers=riverbend.admin)
    again = await harness.client.post(DOMAINS, headers=riverbend.admin, json={"domain": DOMAIN})

    assert (taken.status_code, again.status_code) == (409, 409)
    assert [claim.verified_at is not None for claim in await claim_rows()] == [True, False]


async def test_a_link_emailed_to_an_admin_mailbox_verifies_the_domain_once(harness):
    practice = await practice_with_provider(harness)
    claim_id = await _claim(harness, practice.admin)

    sent = await harness.client.post(
        f"{DOMAINS}/{claim_id}/email", headers=practice.admin, json={"mailbox": "hostmaster"}
    )
    other = await harness.client.post(f"{DOMAINS}/{claim_id}/email", headers=practice.admin, json={"mailbox": "dana"})

    assert (sent.status_code, other.status_code) == (204, 422)
    assert harness.messenger.sent[-1][0] == f"hostmaster@{DOMAIN}"
    token = harness.messenger.last_fragment()
    confirmed = await harness.client.post("/api/domain-verifications", json={"token": token})
    reused = await harness.client.post("/api/domain-verifications", json={"token": token})
    assert confirmed.json() == {"domain": DOMAIN, "practice_name": "Lakeside"}
    assert reused.status_code == 401
    verified = (await _listed(harness, practice.admin))[claim_id]
    assert (verified["verified"], verified["verified_via"]) == (True, "email")
    entries = [entry for entry in await access_log(harness, practice.admin) if entry["action"] == "domain verified"]
    assert [(entry["actor_kind"], entry["actor"]) for entry in entries] == [("system", f"hostmaster@{DOMAIN}")]


async def test_joining_needs_a_verified_domain_and_automatic_joins_never_make_admins(harness):
    practice = await practice_with_provider(harness)
    claim_id = await _claim(harness, practice.admin)
    path = f"{DOMAINS}/{claim_id}/join"

    early = await harness.client.put(path, headers=practice.admin, json={"mode": "request", "role": "viewer"})
    harness.dns.records[DOMAIN] = [(await _listed(harness, practice.admin))[claim_id]["txt_record"]]
    await harness.client.post(f"{DOMAINS}/{claim_id}/check", headers=practice.admin)
    admin = await harness.client.put(path, headers=practice.admin, json={"mode": "auto", "role": "admin"})
    viewer = await harness.client.put(path, headers=practice.admin, json={"mode": "auto", "role": "viewer"})

    assert (early.status_code, admin.status_code, viewer.status_code) == (409, 422, 204)
    claim = (await claim_rows())[0]
    assert (claim.join_mode, claim.join_role) == ("auto", "viewer")
    released = await harness.client.delete(f"{DOMAINS}/{claim_id}", headers=practice.admin)
    assert released.status_code == 204 and await _listed(harness, practice.admin) == {}
    assert (await claim_rows())[0].released_at is not None


async def test_only_practice_admins_manage_the_practice_domains(harness):
    practice = await practice_with_provider(harness)
    await invite_member(harness, practice, name="Cora Diaz", email="cora@lakeside.example.com", role="coder")
    coder = await sign_in(harness.client, "cora@lakeside.example.com")

    assert (await harness.client.get(DOMAINS, headers=coder)).status_code == 403
    assert (await harness.client.post(DOMAINS, headers=coder, json={"domain": DOMAIN})).status_code == 403


async def test_an_organization_claims_a_domain_for_one_of_its_practices(harness):
    group = await organization_of_two(harness)
    domains = organization_path(group, "/domains")

    outside = await harness.client.post(
        domains, headers=group.lakeside.admin, json={"domain": DOMAIN, "practice_id": "no-such-practice"}
    )
    claimed = await harness.client.post(
        domains, headers=group.lakeside.admin, json={"domain": DOMAIN, "practice_id": group.riverbend.id}
    )
    stranger = await harness.client.get(domains, headers=group.riverbend.admin)

    assert (outside.status_code, claimed.status_code, stranger.status_code) == (404, 200, 404)
    listed = (await harness.client.get(domains, headers=group.lakeside.admin)).json()
    assert [(row["domain"], row["practice_name"]) for row in listed] == [(DOMAIN, "Riverbend")]
    assert (await harness.client.get(DOMAINS, headers=group.riverbend.admin)).json() == []
    logged = [entry["action"] for entry in await access_log(harness, group.riverbend.admin)]
    assert "domain claimed" in logged
