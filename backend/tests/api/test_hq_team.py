import pytest
from sqlalchemy import select

from app.core.db import SessionFactory
from app.core.deps import Actor
from app.core.errors import Conflict
from app.models import User
from app.services import hq_team
from tests.builders import ADMIN_SITE, PASSWORD, Harness, create_hq_user, new_practice, sign_in

MAIN_SITE = "https://app.test"
FIRST = "ana@bodha.example.com"
SECOND = "ravi@bodha.example.com"
LAKESIDE_ADMIN = "admin@lakeside.example.com"


async def first_hq(harness: Harness, secrets: dict[str, str], site: str = ADMIN_SITE) -> dict[str, str]:
    await create_hq_user(FIRST)
    return await sign_in(harness.client, FIRST, secret_box=secrets, site=site)


async def invite(harness: Harness, headers: dict[str, str], *, email: str = SECOND, site: str = ADMIN_SITE):
    return await harness.client.post(
        f"{site}/api/hq/team", headers=headers, json={"name": "Ravi Menon", "email": email}
    )


async def second_hq(harness: Harness, headers: dict[str, str], secrets: dict[str, str]) -> dict[str, str]:
    assert (await invite(harness, headers)).status_code == 200
    token = harness.messenger.last_fragment()
    accepted = await harness.client.post(f"{ADMIN_SITE}/api/auth/password", json={"token": token, "password": PASSWORD})
    assert accepted.status_code == 200 and accepted.json()["mfa"] == "setup"
    return await sign_in(harness.client, SECOND, secret_box=secrets, site=ADMIN_SITE)


async def team(harness: Harness, headers: dict[str, str]) -> dict[str, dict]:
    listed = await harness.client.get(f"{ADMIN_SITE}/api/hq/team", headers=headers)
    assert listed.status_code == 200, listed.text
    return {member["email"]: member for member in listed.json()}


async def actions(harness: Harness, headers: dict[str, str]) -> list[tuple[str, str, str]]:
    page = (await harness.client.get(f"{ADMIN_SITE}/api/hq/activity", headers=headers)).json()
    return [(row["action"], row["actor"], row["detail"]) for row in page["items"] if row["action"].startswith("hq ")]


async def test_the_team_lists_only_hq_accounts(harness, two_hosts):
    hq = await first_hq(harness, {})
    await new_practice(harness, name="Lakeside", admin_email=LAKESIDE_ADMIN, hq_headers=hq, hq_site=ADMIN_SITE)
    members = await team(harness, hq)
    assert list(members) == [FIRST]
    first = members[FIRST]
    assert (first["name"], first["status"], first["mfa_enabled"]) == ("Bodha Admin", "active", True)
    assert first["last_active_at"] is not None


async def test_an_invited_hq_member_sets_a_password_on_the_admin_host_then_sets_up_two_step(harness, two_hosts):
    hq = await first_hq(harness, {})
    assert (await invite(harness, hq)).status_code == 200
    to, body = harness.messenger.sent[-1]
    assert to == SECOND
    assert f"{ADMIN_SITE}/set-password#" in body
    assert (await team(harness, hq))[SECOND]["status"] == "invited"
    token = harness.messenger.last_fragment()
    password = {"token": token, "password": PASSWORD}
    assert (await harness.client.post(f"{MAIN_SITE}/api/auth/password", json=password)).status_code == 401
    accepted = await harness.client.post(f"{ADMIN_SITE}/api/auth/password", json=password)
    assert accepted.status_code == 200 and accepted.json()["mfa"] == "setup"
    first = await harness.client.post(f"{ADMIN_SITE}/api/auth/login", json={"email": SECOND, "password": PASSWORD})
    assert first.json()["mfa"] == "setup"
    assert ("hq member invited", "Bodha Admin", "Ravi Menon") in await actions(harness, hq)


async def test_an_hq_invite_refuses_an_hq_email_but_accepts_a_practice_email_on_two_hosts(harness, two_hosts):
    hq = await first_hq(harness, {})
    await new_practice(harness, name="Lakeside", admin_email=LAKESIDE_ADMIN, hq_headers=hq, hq_site=ADMIN_SITE)
    taken = await invite(harness, hq, email=FIRST.upper())
    assert (taken.status_code, taken.json()["message"]) == (409, "someone already uses that email")
    assert (await invite(harness, hq, email=LAKESIDE_ADMIN)).status_code == 200


async def test_on_one_host_an_hq_invite_refuses_a_practice_email_and_links_to_the_main_host(harness):
    hq = await first_hq(harness, {}, site="")
    await new_practice(harness, name="Lakeside", admin_email=LAKESIDE_ADMIN, hq_headers=hq)
    assert (await invite(harness, hq, email=LAKESIDE_ADMIN, site="")).status_code == 409
    assert (await invite(harness, hq, site="")).status_code == 200
    assert f"{MAIN_SITE}/set-password#" in harness.messenger.sent[-1][1]


async def test_only_hq_reaches_the_hq_team(harness, two_hosts):
    hq = await first_hq(harness, {})
    await new_practice(harness, name="Lakeside", admin_email=LAKESIDE_ADMIN, hq_headers=hq, hq_site=ADMIN_SITE)
    practice = await sign_in(harness.client, LAKESIDE_ADMIN, secret_box={}, site=MAIN_SITE)
    assert (await harness.client.get(f"{MAIN_SITE}/api/hq/team", headers=practice)).status_code == 403
    assert (await invite(harness, practice, site=MAIN_SITE)).status_code == 403


async def test_an_invite_can_be_resent_only_while_it_is_pending(harness, two_hosts):
    secrets: dict[str, str] = {}
    hq = await first_hq(harness, secrets)
    member_id = (await invite(harness, hq)).json()["id"]
    sent = len(harness.messenger.sent)
    resent = await harness.client.post(f"{ADMIN_SITE}/api/hq/team/{member_id}/resend-invite", headers=hq)
    assert resent.status_code == 204
    assert len(harness.messenger.sent) == sent + 1 and harness.messenger.sent[-1][0] == SECOND
    first_id = (await team(harness, hq))[FIRST]["id"]
    active = await harness.client.post(f"{ADMIN_SITE}/api/hq/team/{first_id}/resend-invite", headers=hq)
    assert active.status_code == 409
    assert ("hq invite resent", "Bodha Admin", "Ravi Menon") in await actions(harness, hq)


async def test_hq_cannot_deactivate_itself_and_a_deactivated_member_is_signed_out(harness, two_hosts):
    secrets: dict[str, str] = {}
    hq = await first_hq(harness, secrets)
    second = await second_hq(harness, hq, secrets)
    members = await team(harness, hq)
    first_id, second_id = members[FIRST]["id"], members[SECOND]["id"]
    itself = await harness.client.patch(f"{ADMIN_SITE}/api/hq/team/{first_id}", headers=hq, json={"blocked": True})
    assert itself.status_code == 403
    off = await harness.client.patch(f"{ADMIN_SITE}/api/hq/team/{second_id}", headers=hq, json={"blocked": True})
    assert off.status_code == 204
    assert (await harness.client.get(f"{ADMIN_SITE}/api/auth/me", headers=second)).status_code == 401
    login = await harness.client.post(f"{ADMIN_SITE}/api/auth/login", json={"email": SECOND, "password": PASSWORD})
    assert login.status_code == 401
    assert (await team(harness, hq))[SECOND]["status"] == "blocked"
    on = await harness.client.patch(f"{ADMIN_SITE}/api/hq/team/{second_id}", headers=hq, json={"blocked": False})
    assert on.status_code == 204
    assert (await team(harness, hq))[SECOND]["status"] == "active"
    logged = await actions(harness, hq)
    assert ("hq member deactivated", "Bodha Admin", "Ravi Menon") in logged
    assert ("hq member reactivated", "Bodha Admin", "Ravi Menon") in logged


async def test_the_last_active_hq_account_cannot_be_deactivated(harness, two_hosts):
    secrets: dict[str, str] = {}
    hq = await first_hq(harness, secrets)
    await second_hq(harness, hq, secrets)
    async with SessionFactory() as db:
        first = await db.scalar(select(User).where(User.email == FIRST))
        second = await db.scalar(select(User).where(User.email == SECOND))
    off = await harness.client.patch(f"{ADMIN_SITE}/api/hq/team/{second.id}", headers=hq, json={"blocked": True})
    assert off.status_code == 204
    async with SessionFactory() as db:
        with pytest.raises(Conflict, match="keep at least one active HQ account"):
            await hq_team.deactivate_hq_member(db, Actor(second, None, None, None), first.id)
    assert (await team(harness, hq))[FIRST]["status"] == "active"
