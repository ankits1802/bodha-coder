from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, select

from app.core.config import get_settings
from app.core.db import SessionFactory
from app.models import Activity, Practice, User
from tests.builders import PASSWORD, accept_invite, create_hq_user, new_practice, sign_in

EMAIL = "rosa@lakeside.example.com"
SIGNED_UP_BY = "127.0.0.1"


def signup_body(**changes) -> dict:
    body = {
        "name": "Rosa Diaz",
        "practice_name": "Lakeside Family Medicine",
        "email": EMAIL,
        "time_zone": "America/Denver",
        "agreed": True,
    }
    return {key: value for key, value in {**body, **changes}.items() if value is not None}


async def practice_rows() -> list[tuple[Practice, User]]:
    async with SessionFactory() as db:
        rows = await db.execute(select(Practice, User).join(User, User.practice_id == Practice.id))
        return list(rows.tuples().all())


async def hq_headers(harness) -> dict[str, str]:
    await create_hq_user()
    return await sign_in(harness.client, "hq@bodha.example.com")


async def test_email_sign_up_creates_a_trial_practice_with_an_invited_admin(harness):
    response = await harness.client.post("/api/signup", json=signup_body(email="Rosa@Lakeside.example.com"))
    assert (response.status_code, response.content) == (204, b"")
    [(practice, admin)] = await practice_rows()
    denver_today = datetime.now(ZoneInfo("America/Denver")).date()
    assert (practice.name, practice.status, practice.plan, practice.seats) == (
        "Lakeside Family Medicine",
        "trial",
        "trial",
        5,
    )
    assert (practice.time_zone, practice.renews_on) == ("America/Denver", denver_today + timedelta(days=14))
    assert (admin.email, admin.name, admin.role, admin.status) == (EMAIL, "Rosa Diaz", "admin", "invited")
    record = dict(practice.signup)
    accepted_at = datetime.fromisoformat(record.pop("accepted_at"))
    assert abs(datetime.now(accepted_at.tzinfo) - accepted_at) < timedelta(minutes=5)
    assert record == {
        "source": "self",
        "agreement_version": "unpublished",
        "accepted_by": admin.id,
        "method": "email",
        "ip": SIGNED_UP_BY,
    }
    to, body = harness.messenger.sent[-1]
    assert to == EMAIL and "/set-password#" in body
    async with SessionFactory() as db:
        activity = (await db.scalars(select(Activity).where(Activity.action == "practice signed up"))).one()
    assert (activity.practice_id, activity.actor_name) == (practice.id, "Rosa Diaz")
    assert activity.detail == "Lakeside Family Medicine, email"


async def test_the_invited_admin_sets_a_password_and_meets_the_two_step_setup(harness):
    await harness.client.post("/api/signup", json=signup_body())
    await accept_invite(harness)
    login = await harness.client.post("/api/auth/login", json={"email": EMAIL, "password": PASSWORD})
    assert login.status_code == 200
    assert login.json()["mfa"] == "setup"


async def test_an_email_that_already_has_an_account_gets_a_sign_in_email_and_the_same_answer(harness):
    first = await harness.client.post("/api/signup", json=signup_body())
    sent = len(harness.messenger.sent)
    again = await harness.client.post("/api/signup", json=signup_body(email="ROSA@lakeside.example.com"))
    assert (again.status_code, again.content) == (first.status_code, first.content) == (204, b"")
    assert len(harness.messenger.sent) == sent + 1
    to, body = harness.messenger.sent[-1]
    assert to == EMAIL
    assert "already has an account" in body and "/sign-in" in body and "/forgot-password" in body
    assert "/set-password#" not in body
    assert len(await practice_rows()) == 1


async def test_sign_up_needs_the_agreement(harness):
    for body in (signup_body(agreed=False), signup_body(agreed=None)):
        response = await harness.client.post("/api/signup", json=body)
        assert response.status_code == 422
        assert response.json()["error"] == "invalid"
    assert await practice_rows() == []
    assert harness.messenger.sent == []


async def test_sign_up_refuses_an_unknown_time_zone(harness):
    response = await harness.client.post("/api/signup", json=signup_body(time_zone="Mars/Olympus"))
    assert response.status_code == 422
    assert await practice_rows() == []


async def test_sign_up_answers_404_when_it_is_turned_off(harness, monkeypatch):
    monkeypatch.setattr(get_settings(), "self_signup_enabled", False)
    expected = {"error": "not_found", "message": "Self sign-up is not available"}
    response = await harness.client.post("/api/signup", json=signup_body())
    assert (response.status_code, response.json()) == (404, expected)
    pending = await harness.client.get("/api/signup/identity")
    assert (pending.status_code, pending.json()) == (404, expected)
    assert (await harness.client.get("/api/auth/providers")).json()["signup"]["enabled"] is False
    assert await practice_rows() == []


async def test_sign_up_is_limited_to_three_requests_an_hour_for_one_email(harness):
    for _ in range(3):
        assert (await harness.client.post("/api/signup", json=signup_body())).status_code == 204
    limited = await harness.client.post("/api/signup", json=signup_body())
    assert limited.status_code == 429
    assert limited.json() == {"error": "rate_limited", "message": "Too many attempts. Try again in 60 minutes."}


async def test_sign_up_is_limited_to_five_requests_an_hour_from_one_address(harness):
    for number in range(5):
        body = signup_body(email=f"owner{number}@clinic.example.com")
        assert (await harness.client.post("/api/signup", json=body)).status_code == 204
    limited = await harness.client.post("/api/signup", json=signup_body(email="owner9@clinic.example.com"))
    assert limited.status_code == 429
    async with SessionFactory() as db:
        assert await db.scalar(select(func.count()).select_from(Practice)) == 5


async def test_hq_lists_each_practice_with_its_source_and_sign_up_date(harness):
    hq = await hq_headers(harness)
    await new_practice(harness, name="Northside", admin_email="admin@northside.example.com", hq_headers=hq)
    await harness.client.post("/api/signup", json=signup_body())
    listed = {row["name"]: row for row in (await harness.client.get("/api/hq/practices", headers=hq)).json()}
    chicago_today = datetime.now(ZoneInfo("America/Chicago")).date().isoformat()
    denver_today = datetime.now(ZoneInfo("America/Denver")).date().isoformat()
    assert (listed["Northside"]["source"], listed["Northside"]["signed_up_on"]) == ("hq", chicago_today)
    assert (listed["Lakeside Family Medicine"]["source"], listed["Lakeside Family Medicine"]["signed_up_on"]) == (
        "self",
        denver_today,
    )
    async with SessionFactory() as db:
        northside = await db.scalar(select(Practice).where(Practice.name == "Northside"))
    assert northside.signup == {"source": "hq"}
    activity = (
        await harness.client.get("/api/hq/activity", headers=hq, params={"action": "practice signed up"})
    ).json()
    assert [(item["action"], item["detail"]) for item in activity["items"]] == [
        ("practice signed up", "Lakeside Family Medicine, email")
    ]


async def test_the_providers_endpoint_lists_enabled_providers_and_the_sign_up_options(harness, monkeypatch):
    harness.providers["yahoo"].enabled = False
    found = (await harness.client.get("/api/auth/providers")).json()
    assert found["providers"] == ["google", "microsoft"]
    assert found["signup"] == {
        "enabled": True,
        "terms_url": None,
        "baa_url": None,
        "privacy_url": None,
        "test_data_only": True,
    }
    monkeypatch.setattr(get_settings(), "terms_url", "https://bodha.example.com/terms")
    monkeypatch.setattr(get_settings(), "baa_url", "https://bodha.example.com/baa")
    signup = (await harness.client.get("/api/auth/providers")).json()["signup"]
    assert (signup["terms_url"], signup["baa_url"], signup["test_data_only"]) == (
        "https://bodha.example.com/terms",
        "https://bodha.example.com/baa",
        False,
    )
