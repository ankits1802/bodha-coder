import pyotp
from sqlalchemy import func, select

from app.core.config import get_settings
from app.core.db import SessionFactory
from app.models import Practice, User
from tests.api.membership_helpers import REFRESH, SAM, signed_in
from tests.builders import back_from, forget_last_code, practice_people, practice_with_member

NEW_PRACTICE = {"practice_name": "Harbor Pediatrics", "time_zone": "America/New_York", "agreed": True}
IDENTITY_FORM = {"name": "Sam Patel", **NEW_PRACTICE}


async def counted(table) -> int:
    async with SessionFactory() as db:
        return await db.scalar(select(func.count()).select_from(table))


async def finish_two_step(harness, email: str, mfa_token: str) -> dict:
    setup = await harness.client.post("/api/auth/mfa/setup", json={"mfa_token": mfa_token})
    await forget_last_code(email)
    code = pyotp.TOTP(setup.json()["secret"]).now()
    verified = await harness.client.post("/api/auth/mfa/verify", json={"mfa_token": mfa_token, "code": code})
    assert verified.status_code == 200, verified.text
    return verified.json()


async def test_email_sign_up_with_an_existing_account_asks_to_sign_in_and_add_the_practice(harness):
    await practice_with_member(harness, name="Sam Patel", email=SAM, role="coder")
    body = {"name": "Sam Patel", "email": SAM.upper(), **NEW_PRACTICE}
    answered = await harness.client.post("/api/signup", json=body)
    assert (answered.status_code, answered.content) == (204, b"")
    to, mail = harness.messenger.sent[-1]
    assert to == SAM and "/sign-in?next=/practices/new" in mail and "/set-password#" not in mail
    assert await counted(Practice) == 1


async def test_a_signed_in_person_starts_another_practice_and_becomes_its_first_admin(harness):
    await practice_with_member(harness, name="Sam Patel", email=SAM, role="coder")
    sam = await signed_in(harness, SAM)
    harness.client.cookies.set("bodha_refresh", sam.refresh, **REFRESH)
    started = await harness.client.post("/api/auth/practices", headers=sam.headers, json=NEW_PRACTICE)
    assert started.status_code == 200, started.text
    assert started.json()["mfa"] == "setup"
    signed = await finish_two_step(harness, SAM, started.json()["mfa_token"])
    assert signed["user"]["practice"]["name"] == "Harbor Pediatrics"
    assert signed["user"]["role"] == "admin"
    assert [(choice["name"], choice["role"]) for choice in signed["user"]["practices"]] == [
        ("Harbor Pediatrics", "admin"),
        ("Lakeside", "coder"),
    ]
    harbor = [
        (practice, member)
        for practice, person, member in await practice_people()
        if practice.name == "Harbor Pediatrics"
    ]
    [(practice, membership)] = harbor
    assert (practice.status, practice.plan, practice.signup["method"]) == ("trial", "trial", "account")
    assert (membership.role, membership.status) == ("admin", "active")
    assert await counted(User) == 3


async def test_starting_another_practice_needs_the_agreement_and_open_sign_up(harness, monkeypatch):
    await practice_with_member(harness, name="Sam Patel", email=SAM, role="coder")
    sam = await signed_in(harness, SAM)
    refused = await harness.client.post(
        "/api/auth/practices", headers=sam.headers, json={**NEW_PRACTICE, "agreed": False}
    )
    assert refused.status_code == 422
    monkeypatch.setattr(get_settings(), "self_signup_enabled", False)
    assert (await harness.client.post("/api/auth/practices", headers=sam.headers, json=NEW_PRACTICE)).status_code == 404
    assert await counted(Practice) == 1


async def test_sign_up_with_a_provider_for_an_existing_account_creates_the_practice_for_that_account(harness):
    await practice_with_member(harness, name="Sam Patel", email=SAM, role="coder")
    harness.google.returns("code-7", subject="google-sam", email=SAM, name="Sam P")
    back = await back_from(harness, "google", "code-7", intent="signup")
    assert back.headers["location"] == f"{get_settings().app_url}/sign-up/practice"
    pending = await harness.client.get("/api/signup/identity")
    assert pending.json()["has_account"] is True
    created = await harness.client.post("/api/signup/identity", json=IDENTITY_FORM)
    assert created.status_code == 200, created.text
    signed = await finish_two_step(harness, SAM, created.json()["mfa_token"])
    assert signed["user"]["practice"]["name"] == "Harbor Pediatrics"
    sam = [(practice.name, member.role) for practice, person, member in await practice_people() if person.email == SAM]
    assert sam == [("Lakeside", "coder"), ("Harbor Pediatrics", "admin")]
    assert await counted(User) == 3


async def test_without_the_sign_up_intent_a_provider_signs_an_existing_account_in(harness):
    await practice_with_member(harness, name="Sam Patel", email=SAM, role="coder")
    harness.google.returns("code-8", subject="google-sam", email=SAM, name="Sam P")
    back = await back_from(harness, "google", "code-8")
    assert back.headers["location"] == f"{get_settings().app_url}/sign-in#signed_in"
    assert await counted(Practice) == 1
