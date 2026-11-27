import pyotp
import pytest
from sqlalchemy import select

from app.adapters.oidc_providers import UnverifiedEmail
from app.core.config import get_settings
from app.core.db import SessionFactory
from app.core.security import issue_token
from app.models import Practice, User, UserIdentity
from tests.builders import back_from, forget_last_code, practice_people, practice_with_member, sign_in_page

SIGNUP_COOKIE = {"domain": "app.test", "path": "/api/signup"}
OWNER = "omar@harbor.example.com"
FORM = {"name": "Omar Haddad", "practice_name": "Harbor Pediatrics", "time_zone": "America/New_York", "agreed": True}


async def arrive_at_sign_up(harness, provider: str = "google", *, email: str = OWNER, subject: str = "subject-1"):
    harness.providers[provider].returns("code-1", subject=subject, email=email, name="Omar Haddad")
    return await back_from(harness, provider, "code-1")


async def identities() -> list[tuple[str, str, str]]:
    async with SessionFactory() as db:
        query = select(User.email, UserIdentity.provider, UserIdentity.subject).select_from(UserIdentity)
        rows = await db.execute(query.join(User, User.id == UserIdentity.user_id))
        return [tuple(row) for row in rows.all()]


async def test_a_verified_identity_without_an_account_goes_to_sign_up_with_a_cookie_and_nothing_in_the_url(harness):
    back = await arrive_at_sign_up(harness)
    assert back.status_code == 302
    assert back.headers["location"] == f"{get_settings().app_url}/sign-up/practice"
    cookie = [value.lower() for value in back.headers.get_list("set-cookie") if value.startswith("bodha_signup=")][0]
    assert all(part in cookie for part in ("httponly", "secure", "samesite=lax", "path=/api/signup", "max-age=1800"))
    assert harness.client.cookies.get("bodha_signup", **SIGNUP_COOKIE)
    pending = await harness.client.get("/api/signup/identity")
    assert pending.json() == {"email": OWNER, "name": "Omar Haddad", "provider": "google", "has_account": False}


@pytest.mark.parametrize("provider", ["google", "microsoft", "yahoo"])
async def test_completing_sign_up_creates_an_active_admin_bound_to_the_identity(harness, provider):
    await arrive_at_sign_up(harness, provider)
    created = await harness.client.post("/api/signup/identity", json=FORM)
    assert created.status_code == 200, created.text
    assert created.json()["mfa"] == "setup"
    cleared = [value for value in created.headers.get_list("set-cookie") if value.startswith("bodha_signup=")]
    assert cleared and "max-age=0" in cleared[0].lower()
    assert harness.client.cookies.get("bodha_signup", **SIGNUP_COOKIE) is None
    assert await identities() == [(OWNER, provider, "subject-1")]
    [(practice, admin, membership)] = await practice_people()
    assert membership.role == "admin"
    assert (practice.status, practice.plan, practice.seats, practice.time_zone) == (
        "trial",
        "trial",
        5,
        "America/New_York",
    )
    assert (admin.role, admin.status, admin.name) == ("admin", "active", "Omar Haddad")
    assert (practice.signup["source"], practice.signup["method"], practice.signup["accepted_by"]) == (
        "self",
        provider,
        admin.id,
    )


async def test_the_new_admin_continues_into_two_step_setup_and_signs_in(harness):
    await arrive_at_sign_up(harness)
    challenge = (await harness.client.post("/api/signup/identity", json=FORM)).json()
    setup = await harness.client.post("/api/auth/mfa/setup", json={"mfa_token": challenge["mfa_token"]})
    assert setup.status_code == 200
    await forget_last_code(OWNER)
    code = pyotp.TOTP(setup.json()["secret"]).now()
    verified = await harness.client.post(
        "/api/auth/mfa/verify", json={"mfa_token": challenge["mfa_token"], "code": code}
    )
    assert verified.status_code == 200
    assert verified.json()["user"]["practice"]["name"] == "Harbor Pediatrics"
    assert len(verified.json()["recovery_codes"]) == 10


async def test_a_missing_or_expired_sign_up_cookie_is_refused(harness):
    assert (await harness.client.get("/api/signup/identity")).status_code == 401
    assert (await harness.client.post("/api/signup/identity", json=FORM)).status_code == 401
    expired = issue_token("signup", "subject-1", -1, idp="google", email=OWNER, name="Omar Haddad")
    harness.client.cookies.set("bodha_signup", expired, **SIGNUP_COOKIE)
    assert (await harness.client.get("/api/signup/identity")).status_code == 401
    assert (await harness.client.post("/api/signup/identity", json=FORM)).status_code == 401
    async with SessionFactory() as db:
        assert (await db.scalars(select(Practice))).all() == []


async def test_completing_sign_up_needs_the_agreement_and_a_name(harness):
    await arrive_at_sign_up(harness)
    for changes in ({"agreed": False}, {"name": ""}, {"practice_name": "H"}):
        response = await harness.client.post("/api/signup/identity", json={**FORM, **changes})
        assert response.status_code == 422
    assert await identities() == []


async def test_an_email_that_gained_an_account_meanwhile_becomes_admin_of_the_new_practice(harness):
    await arrive_at_sign_up(harness, email="sam@lakeside.example.com")
    await practice_with_member(harness, name="Sam Patel", email="sam@lakeside.example.com", role="coder")
    response = await harness.client.post("/api/signup/identity", json=FORM)
    assert response.status_code == 200, response.text
    assert response.json()["mfa"] == "setup"
    people = await practice_people()
    sam = [(practice.name, member.role) for practice, person, member in people if person.name == "Sam Patel"]
    assert sam == [("Lakeside", "coder"), ("Harbor Pediatrics", "admin")]


async def test_a_microsoft_account_without_a_verified_email_is_sent_back_with_its_reason(harness):
    harness.providers["microsoft"].refusals["code-1"] = UnverifiedEmail("this Microsoft account has no verified email")
    back = await back_from(harness, "microsoft", "code-1")
    assert back.headers["location"] == sign_in_page("error=unverified_email&provider=microsoft")
    assert harness.client.cookies.get("bodha_signup", **SIGNUP_COOKIE) is None


async def test_each_provider_binds_its_own_subject_and_refuses_another_for_the_same_email(harness):
    await practice_with_member(harness, name="Sam Patel", email="sam@lakeside.example.com", role="coder")
    for provider in ("google", "microsoft"):
        back = await arrive_at_sign_up(harness, provider, email="sam@lakeside.example.com", subject=f"{provider}-sam")
        assert back.headers["location"] == sign_in_page("signed_in")
    impostor = await arrive_at_sign_up(harness, "microsoft", email="sam@lakeside.example.com", subject="other")
    assert impostor.headers["location"] == sign_in_page("error=mismatch&provider=microsoft")
    assert sorted(await identities()) == [
        ("sam@lakeside.example.com", "google", "google-sam"),
        ("sam@lakeside.example.com", "microsoft", "microsoft-sam"),
    ]


async def test_a_subject_bound_to_another_account_cannot_start_a_sign_up(harness):
    await practice_with_member(harness, name="Sam Patel", email="sam@lakeside.example.com", role="coder")
    await arrive_at_sign_up(harness, "yahoo", email="sam@lakeside.example.com", subject="yahoo-sam")
    back = await arrive_at_sign_up(harness, "yahoo", email="new@harbor.example.com", subject="yahoo-sam")
    assert back.headers["location"] == sign_in_page("error=mismatch&provider=yahoo")


async def test_an_unknown_provider_is_not_found(harness):
    assert (await harness.client.get("/api/auth/facebook/start")).status_code == 404
