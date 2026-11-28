from app.scripts.lift_sso_requirement import lift, main
from tests.api.membership_helpers import access_log
from tests.api.sso_helpers import ANNA, save_settings, settings_body, sso_ready
from tests.builders import PASSWORD, invite_member, practice_with_provider


async def test_support_can_lift_a_requirement_when_no_admin_can_sign_in(harness, idp):
    practice = await practice_with_provider(harness)
    await invite_member(harness, practice, name="Anna Reyes", email=ANNA, role="coder")
    setup = await sso_ready(harness, practice, idp)
    admin_id = (await harness.client.get("/api/auth/me", headers=practice.admin)).json()["id"]
    body = settings_body((idp,), claim_ids=[setup.claim_id], required=True, break_glass=[admin_id])
    assert (await save_settings(harness, practice.admin, body)).status_code == 200
    blocked = await harness.client.post("/api/auth/login", json={"email": ANNA, "password": PASSWORD})

    lifted = await lift(setup.connection_id, "IdP certificate expired, ticket 4821")
    again = await lift(setup.connection_id, "IdP certificate expired, ticket 4821")

    assert blocked.status_code == 403
    assert lifted == (0, f"{setup.connection_id}: single sign-on no longer required (version 3)")
    assert again == (1, f"{setup.connection_id}: single sign-on is not required for this connection")
    signed_in = await harness.client.post("/api/auth/login", json={"email": ANNA, "password": PASSWORD})
    assert signed_in.status_code == 200, signed_in.text
    view = (await harness.client.get("/api/practice/sso", headers=practice.admin)).json()["connection"]
    assert (view["history"][0]["author_name"], view["current"]["required"]) == ("Bodha support", False)
    assert view["current"]["claim_ids"] == [setup.claim_id]
    entries = [(entry["action"], entry["detail"]) for entry in await access_log(harness, practice.admin)]
    detail = "version 3: required off by Bodha support: IdP certificate expired, ticket 4821"
    assert ("single sign-on changed", detail) in entries


async def test_the_script_needs_a_connection_and_a_reason(capsys):
    assert main([]) == 2
    assert capsys.readouterr().err.startswith("usage: python -m app.scripts.lift_sso_requirement")
    assert await lift("missing", "x") == (1, "missing: give the reason the customer asked for this")
    assert await lift("missing", "ticket 1") == (1, "missing: single sign-on connection not found")
