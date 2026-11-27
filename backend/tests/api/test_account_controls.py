from datetime import datetime
from zoneinfo import ZoneInfo

from tests.builders import (
    PASSWORD,
    back_from_google,
    practice_with_member,
    practice_with_provider,
    sign_in,
    sign_in_page,
)

ADMIN = "admin@lakeside.example.com"
CODER = "sam@lakeside.example.com"
ENDED = "This practice's plan ended on 2025-12-31"


async def member_id(harness, practice, email: str) -> str:
    members = (await harness.client.get("/api/team", headers=practice.admin)).json()["members"]
    return {member["email"]: member["id"] for member in members}[email]


async def test_an_admin_reset_email_ends_sessions_only_once_the_password_is_set(harness):
    practice = await practice_with_member(harness, name="Sam Patel", email=CODER, role="coder")
    coder = await sign_in(harness.client, CODER)
    target = await member_id(harness, practice, CODER)
    sent = await harness.client.post(f"/api/team/{target}/reset-password", headers=practice.admin)
    assert sent.status_code == 204
    assert harness.messenger.sent[-1][0] == CODER
    assert (await harness.client.get("/api/auth/me", headers=coder)).status_code == 200
    token = harness.messenger.last_fragment()
    chosen = await harness.client.post("/api/auth/password", json={"token": token, "password": "fresh-password-9"})
    assert chosen.status_code == 204
    assert (await harness.client.get("/api/auth/me", headers=coder)).status_code == 401


async def test_an_admin_cannot_reset_a_password_in_another_practice(harness):
    lakeside = await practice_with_member(harness, name="Sam Patel", email=CODER, role="coder")
    target = await member_id(harness, lakeside, CODER)
    riverbend = await practice_with_provider(harness, name="Riverbend", admin_email="admin@riverbend.example.com")
    refused = await harness.client.post(f"/api/team/{target}/reset-password", headers=riverbend.admin)
    assert refused.status_code == 404


async def test_a_practice_past_its_renewal_date_is_refused_outside_billing_but_hq_is_not(harness):
    practice = await practice_with_member(harness, name="Sam Patel", email=CODER, role="coder")
    hq = await sign_in(harness.client, f"hq-{ADMIN}", secret_box=practice.secrets)
    patch = {"renews_on": "2025-12-31"}
    assert (await harness.client.patch(f"/api/hq/practices/{practice.id}", headers=hq, json=patch)).status_code == 204
    refused = await harness.client.get("/api/today", headers=practice.admin)
    assert refused.status_code == 403
    assert refused.json() == {"error": "plan_ended", "message": ENDED}
    assert (await harness.client.get("/api/plan", headers=practice.admin)).status_code == 200
    login = await harness.client.post("/api/auth/login", json={"email": CODER, "password": PASSWORD})
    assert login.status_code == 403 and login.json()["message"] == ENDED
    harness.google.returns("code-1", subject="google-sam", email=CODER)
    assert (await back_from_google(harness, "code-1")).headers["location"] == sign_in_page(
        "error=plan_ended&provider=google"
    )
    assert (await harness.client.get("/api/hq/practices", headers=hq)).status_code == 200


async def test_a_practice_can_still_work_on_its_renewal_day(harness):
    practice = await practice_with_provider(harness)
    hq = await sign_in(harness.client, f"hq-{ADMIN}", secret_box=practice.secrets)
    today = datetime.now(ZoneInfo("America/Chicago")).date().isoformat()
    await harness.client.patch(f"/api/hq/practices/{practice.id}", headers=hq, json={"renews_on": today})
    assert (await harness.client.get("/api/today", headers=practice.admin)).status_code == 200


async def test_security_settings_have_no_private_messages_switch(harness):
    practice = await practice_with_provider(harness)
    setup = (await harness.client.get("/api/practice/setup", headers=practice.admin)).json()
    assert setup["security"] == {"mfa_roles": ["admin", "compliance"], "idle_minutes": 15, "access_log_years": 7}
    old = {"mfa_roles": ["admin"], "idle_minutes": 10, "private_messages": False}
    assert (await harness.client.put("/api/practice/security", headers=practice.admin, json=old)).status_code == 422
    new = {"mfa_roles": ["admin"], "idle_minutes": 10}
    assert (await harness.client.put("/api/practice/security", headers=practice.admin, json=new)).status_code == 204
