import hashlib

import pyotp
from sqlalchemy import select

from app.core.db import SessionFactory
from app.models import Activity, AuthEvent, User
from tests.api.membership_helpers import (
    REFRESH,
    SAM,
    access_log,
    auth_events,
    signed_in,
    switch,
    two_practices,
)
from tests.builders import (
    PASSWORD,
    create_hq_user,
    forget_last_code,
    practice_with_member,
    practice_with_provider,
    sign_in,
)

BROWSER = {"user-agent": "Mozilla/5.0 (Macintosh) Safari/605.1"}
HQ = "hq@bodha.example.com"
RITA = "rita@lakeside.example.com"


def hashed(email: str) -> str:
    return hashlib.sha256(email.strip().lower().encode()).hexdigest()


async def user_id(email: str) -> str:
    async with SessionFactory() as db:
        return await db.scalar(select(User.id).where(User.email == email))


async def every_event() -> list[AuthEvent]:
    async with SessionFactory() as db:
        return list((await db.scalars(select(AuthEvent))).all())


async def test_a_wrong_password_and_an_unknown_email_are_recorded_with_a_hash_of_the_email_only(harness):
    practice = await practice_with_member(harness, name="Sam Patel", email=SAM, role="coder")
    wrong = {"email": "Sam@Lakeside.example.com", "password": "not-the-password"}
    assert (await harness.client.post("/api/auth/login", json=wrong, headers=BROWSER)).status_code == 401
    unknown = {"email": "nobody@nowhere.example.com", "password": "whatever-it-is"}
    assert (await harness.client.post("/api/auth/login", json=unknown, headers=BROWSER)).status_code == 401
    failed = await auth_events("sign_in_failed")
    assert [(event.user_id, event.email_hash) for event in failed] == [
        (await user_id(SAM), hashed(SAM)),
        (None, hashed("nobody@nowhere.example.com")),
    ]
    assert all(event.user_agent == BROWSER["user-agent"] and event.ip for event in failed)
    stored = " ".join(str(value) for event in await every_event() for value in vars(event).values())
    assert "nowhere.example.com" not in stored and "not-the-password" not in stored
    entries = [(row["actor"], row["action"]) for row in await access_log(harness, practice.admin)]
    assert ("Sam Patel", "sign-in failed") in entries


async def test_a_sign_in_is_recorded_with_its_practice_address_and_browser(harness):
    practice = await practice_with_member(harness, name="Sam Patel", email=SAM, role="coder")
    signed = await harness.client.post("/api/auth/login", json={"email": SAM, "password": PASSWORD}, headers=BROWSER)
    assert signed.status_code == 200
    [event] = [event for event in await auth_events("signed_in") if event.user_id == await user_id(SAM)]
    assert (event.practice_id, event.realm, event.detail) == (practice.id, "practice", "with password")
    assert event.ip and event.user_agent == BROWSER["user-agent"]
    entries = [(row["actor"], row["action"], row["user_agent"]) for row in await access_log(harness, practice.admin)]
    assert ("Sam Patel", "signed in", BROWSER["user-agent"]) in entries


async def test_an_hq_sign_in_now_carries_the_address_and_browser_into_hq_activity(harness):
    await create_hq_user()
    await sign_in(harness.client, HQ, secret_box={})
    [event] = await auth_events("signed_in")
    assert (event.realm, event.practice_id) == ("hq", None)
    assert event.ip
    async with SessionFactory() as db:
        details = list(await db.scalars(select(Activity.detail).where(Activity.action == "signed in")))
    assert details == [f"with password, {event.ip}"]


async def test_setting_a_password_from_an_invite_and_from_a_reset_are_recorded(harness):
    practice = await practice_with_member(harness, name="Sam Patel", email=SAM, role="coder")
    target = await user_id(SAM)
    assert [event.user_id for event in await auth_events("password_set")][-1] == target
    sent = await harness.client.post(f"/api/team/{target}/reset-password", headers=practice.admin)
    assert sent.status_code == 204
    token = harness.messenger.last_fragment()
    chosen = await harness.client.post("/api/auth/password", json={"token": token, "password": "fresh-password-9"})
    assert chosen.status_code == 204
    assert [event.user_id for event in await auth_events("password_changed")] == [target]


async def test_two_step_on_off_and_recovery_codes_are_recorded(harness):
    practice = await practice_with_provider(harness)
    person = {"name": "Rita Moss", "email": RITA, "role": "compliance"}
    invited = await harness.client.post("/api/team", headers=practice.admin, json=person)
    token = harness.messenger.last_fragment()
    await harness.client.post("/api/auth/password", json={"token": token, "password": PASSWORD})
    login = (await harness.client.post("/api/auth/login", json={"email": RITA, "password": PASSWORD})).json()
    secret = (await harness.client.post("/api/auth/mfa/setup", json={"mfa_token": login["mfa_token"]})).json()["secret"]
    verified = await harness.client.post(
        "/api/auth/mfa/verify", json={"mfa_token": login["mfa_token"], "code": pyotp.TOTP(secret).now()}
    )
    codes = verified.json()["recovery_codes"]
    headers = {"Authorization": f"Bearer {verified.json()['access_token']}"}
    await forget_last_code(RITA)
    current = {"code": pyotp.TOTP(secret).now()}
    replaced = await harness.client.post("/api/auth/recovery-codes", headers=headers, json=current)
    assert replaced.status_code == 200
    again = (await harness.client.post("/api/auth/login", json={"email": RITA, "password": PASSWORD})).json()
    recovered = await harness.client.post(
        "/api/auth/mfa/recover", json={"mfa_token": again["mfa_token"], "recovery_code": replaced.json()["codes"][0]}
    )
    assert recovered.status_code == 200 and codes
    reset = await harness.client.post(f"/api/team/{invited.json()['id']}/reset-mfa", headers=practice.admin)
    assert reset.status_code == 204
    rita = invited.json()["id"]
    for kind in ("two_step_on", "recovery_codes_replaced", "recovery_code_used", "two_step_off"):
        assert [event.user_id for event in await auth_events(kind)].count(rita) == 1, kind
    assert [event.detail for event in await auth_events("two_step_off")] == ["by Practice Admin"]


async def test_signing_out_and_ending_sessions_are_recorded(harness):
    await practice_with_member(harness, name="Sam Patel", email=SAM, role="coder")
    target = await user_id(SAM)
    first = await signed_in(harness, SAM)
    current = await signed_in(harness, SAM)
    listed = (await harness.client.get("/api/auth/sessions", headers=current.headers)).json()
    other = next(device["id"] for device in listed if not device["current"])
    assert (await harness.client.delete(f"/api/auth/sessions/{other}", headers=current.headers)).status_code == 204
    harness.client.cookies.set("bodha_refresh", current.refresh, **REFRESH)
    assert (await harness.client.post("/api/auth/logout")).status_code == 204
    revoked = await auth_events("session_revoked")
    assert [(event.user_id, event.detail) for event in revoked] == [(target, "one device")]
    [signed_out] = await auth_events("signed_out")
    assert signed_out.user_id == target and signed_out.practice_id is not None
    assert first.refresh != current.refresh


async def test_a_practice_switch_is_recorded_with_the_practice_entered(harness):
    both = await two_practices(harness)
    sam = await signed_in(harness, SAM)
    assert (await switch(harness, sam, both.riverbend.id)).status_code == 200
    [event] = await auth_events("practice_switched")
    assert (event.user_id, event.practice_id) == (both.sam_id, both.riverbend.id)


async def test_events_are_shown_only_to_the_practices_of_the_person(harness):
    both = await two_practices(harness)
    outsider = await practice_with_provider(harness, name="Harbor", admin_email="admin@harbor.example.com")
    await harness.client.post("/api/auth/login", json={"email": SAM, "password": "not-the-password"})
    lakeside = [row["action"] for row in await access_log(harness, both.lakeside.admin) if row["actor"] == "Sam Patel"]
    harbor = [row["action"] for row in await access_log(harness, outsider.admin) if row["actor"] == "Sam Patel"]
    assert "sign-in failed" in lakeside and harbor == []
