from tests.builders import (
    PASSWORD,
    Harness,
    create_hq_user,
    new_practice,
    practice_with_provider,
    sign_in,
)

SETUP = "/api/practice/setup"
DISMISS = "/api/practice/first-run/dismissed"
BARE_ADMIN = "owner@harbor.example.com"
ALL_ROLES = ["admin", "biller", "cdi", "coder", "compliance", "viewer"]
CHECKS = {"em": True, "icd": True, "cdi": True, "audit": True, "mips": False, "hcc": False}


async def first_run(harness: Harness, headers: dict[str, str]) -> dict[str, bool]:
    response = await harness.client.get(SETUP, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()["first_run"]


async def practice_without_providers(harness: Harness) -> dict[str, str]:
    secrets: dict[str, str] = {}
    await create_hq_user(f"hq-{BARE_ADMIN}")
    hq = await sign_in(harness.client, f"hq-{BARE_ADMIN}", secret_box=secrets)
    await new_practice(harness, name="Harbor View", admin_email=BARE_ADMIN, hq_headers=hq)
    return await sign_in(harness.client, BARE_ADMIN, secret_box=secrets)


async def invite(harness: Harness, headers: dict[str, str], email: str, role: str) -> str:
    person = {"name": "New Person", "email": email, "role": role}
    assert (await harness.client.post("/api/team", headers=headers, json=person)).status_code == 200
    return harness.messenger.last_fragment()


async def test_saving_the_checks_and_the_security_marks_each_first_step_reviewed(harness):
    practice = await practice_with_provider(harness)
    assert await first_run(harness, practice.admin) == {"checks": False, "security": False, "dismissed": False}
    kept = await harness.client.put("/api/practice/checks", headers=practice.admin, json={"checks": CHECKS})
    assert kept.status_code == 204
    assert await first_run(harness, practice.admin) == {"checks": True, "security": False, "dismissed": False}
    recommended = {"mfa_roles": ALL_ROLES, "idle_minutes": 15, "access_log_years": 7}
    saved = await harness.client.put("/api/practice/security", headers=practice.admin, json=recommended)
    assert saved.status_code == 204
    assert await first_run(harness, practice.admin) == {"checks": True, "security": True, "dismissed": False}


async def test_the_first_steps_can_be_hidden_only_once_a_provider_is_added(harness):
    bare = await practice_without_providers(harness)
    refused = await harness.client.put(DISMISS, headers=bare)
    assert (refused.status_code, refused.json()["message"]) == (409, "add a provider before hiding the first steps")
    assert (await first_run(harness, bare))["dismissed"] is False
    practice = await practice_with_provider(harness)
    assert (await harness.client.put(DISMISS, headers=practice.admin)).status_code == 204
    assert (await first_run(harness, practice.admin))["dismissed"] is True
    assert (await harness.client.put(DISMISS, headers=practice.admin)).status_code == 204


async def test_only_an_admin_hides_the_first_steps(harness):
    practice = await practice_with_provider(harness)
    token = await invite(harness, practice.admin, "sam@lakeside.example.com", "coder")
    signed = await harness.client.post("/api/auth/password", json={"token": token, "password": PASSWORD})
    coder = {"Authorization": f"Bearer {signed.json()['access_token']}"}
    assert (await harness.client.put(DISMISS, headers=coder)).status_code == 403


async def test_setting_a_password_signs_in_or_starts_two_step_setup_when_the_role_needs_it(harness):
    practice = await practice_with_provider(harness)
    coder_token = await invite(harness, practice.admin, "sam@lakeside.example.com", "coder")
    coder = await harness.client.post("/api/auth/password", json={"token": coder_token, "password": PASSWORD})
    assert coder.status_code == 200
    assert (coder.json()["user"]["role"], coder.json()["user"]["practice"]["id"]) == ("coder", practice.id)
    headers = {"Authorization": f"Bearer {coder.json()['access_token']}"}
    assert (await harness.client.get("/api/auth/me", headers=headers)).status_code == 200
    assert (await harness.client.post("/api/auth/refresh")).status_code == 200
    admin_token = await invite(harness, practice.admin, "lee@lakeside.example.com", "admin")
    admin = await harness.client.post("/api/auth/password", json={"token": admin_token, "password": PASSWORD})
    assert admin.status_code == 200
    assert admin.json()["mfa"] == "setup" and "access_token" not in admin.json()
    setup = await harness.client.post("/api/auth/mfa/setup", json={"mfa_token": admin.json()["mfa_token"]})
    assert setup.status_code == 200 and setup.json()["secret"]
