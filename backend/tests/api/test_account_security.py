from urllib.parse import parse_qs, urlsplit

from app.adapters.google_oidc import GoogleIdentity
from tests.builders import (
    PASSWORD,
    back_from_google,
    pass_two_step,
    practice_with_member,
    practice_with_provider,
    sign_in,
    sign_in_page,
)

ADMIN = "admin@lakeside.example.com"
CODER = "sam@lakeside.example.com"
NEW_PASSWORD = "brand-new-password-42"
REFRESH = {"domain": "app.test", "path": "/api/auth"}


async def practice_with_coder(harness):
    return await practice_with_member(harness, name="Sam Patel", email=CODER, role="coder")


async def test_forgot_password_answers_the_same_whether_or_not_the_account_exists(harness):
    await practice_with_coder(harness)
    before = len(harness.messenger.sent)
    unknown = await harness.client.post("/api/auth/forgot", json={"email": "nobody@lakeside.example.com"})
    assert unknown.status_code == 204
    assert len(harness.messenger.sent) == before
    known = await harness.client.post("/api/auth/forgot", json={"email": "SAM@lakeside.example.com"})
    assert known.status_code == 204
    assert known.content == unknown.content == b""
    assert len(harness.messenger.sent) == before + 1
    assert harness.messenger.sent[-1][0] == CODER


async def test_a_reset_link_works_once_and_ends_existing_sessions(harness):
    await practice_with_coder(harness)
    coder = await sign_in(harness.client, CODER)
    await harness.client.post("/api/auth/forgot", json={"email": CODER})
    token = harness.messenger.last_fragment()
    first = await harness.client.post("/api/auth/password", json={"token": token, "password": NEW_PASSWORD})
    assert first.status_code == 204
    assert (await harness.client.get("/api/auth/me", headers=coder)).status_code == 401
    assert (await harness.client.post("/api/auth/refresh")).status_code == 401
    again = await harness.client.post("/api/auth/password", json={"token": token, "password": "another-pass-77"})
    assert again.status_code == 401
    login = await harness.client.post("/api/auth/login", json={"email": CODER, "password": NEW_PASSWORD})
    assert "access_token" in login.json()


async def test_google_refuses_an_email_without_an_account(harness):
    await practice_with_coder(harness)
    harness.google.identities["code-1"] = GoogleIdentity(sub="google-1", email="stranger@example.com")
    back = await back_from_google(harness, "code-1")
    assert back.status_code == 302
    assert back.headers["location"] == sign_in_page("error=no_account")


async def test_google_signs_in_a_known_email_and_sets_the_refresh_cookie(harness):
    practice = await practice_with_coder(harness)
    harness.client.cookies.clear()
    harness.google.identities["code-2"] = GoogleIdentity(sub="google-sam", email=CODER)
    back = await back_from_google(harness, "code-2")
    assert back.headers["location"] == sign_in_page("signed_in")
    assert harness.client.cookies.get("bodha_refresh", **REFRESH)
    refreshed = await harness.client.post("/api/auth/refresh")
    assert refreshed.status_code == 200 and refreshed.json()["user"]["email"] == CODER
    log = (await harness.client.get("/api/access-log", headers=practice.admin)).json()
    assert {"actor": "Sam Patel", "action": "signed in", "detail": "with Google"} in [
        {key: entry[key] for key in ("actor", "action", "detail")} for entry in log
    ]


async def test_google_sends_a_two_step_role_to_the_code_step(harness):
    practice = await practice_with_coder(harness)
    harness.client.cookies.clear()
    harness.google.identities["code-3"] = GoogleIdentity(sub="google-admin", email=ADMIN)
    back = await back_from_google(harness, "code-3")
    fragment = urlsplit(back.headers["location"]).fragment
    assert back.headers["location"].startswith(sign_in_page("mfa="))
    assert parse_qs(fragment)["setup"] == ["0"]
    assert harness.client.cookies.get("bodha_refresh", **REFRESH) is None
    signed_in = await pass_two_step(harness.client, ADMIN, parse_qs(fragment)["mfa"][0], practice.secrets[ADMIN])
    assert signed_in["user"]["email"] == ADMIN


async def test_google_refuses_a_different_google_account_for_a_bound_email(harness):
    await practice_with_coder(harness)
    harness.google.identities["first"] = GoogleIdentity(sub="google-sam", email=CODER)
    harness.google.identities["other"] = GoogleIdentity(sub="google-impostor", email=CODER)
    assert (await back_from_google(harness, "first")).headers["location"] == sign_in_page("signed_in")
    back = await back_from_google(harness, "other")
    assert back.headers["location"] == sign_in_page("error=mismatch")


async def test_google_refuses_a_state_that_does_not_match_the_cookie(harness):
    await practice_with_coder(harness)
    harness.google.identities["code-4"] = GoogleIdentity(sub="google-sam", email=CODER)
    await harness.client.get("/api/auth/google/start")
    back = await harness.client.get("/api/auth/google/callback", params={"code": "code-4", "state": "forged"})
    assert back.headers["location"] == sign_in_page("error=failed")
    assert harness.google.exchanges == []


async def test_google_activates_an_invited_member(harness):
    practice = await practice_with_provider(harness)
    await harness.client.post(
        "/api/team",
        headers=practice.admin,
        json={"name": "Ana Cruz", "email": "ana@lakeside.example.com", "role": "biller"},
    )
    harness.google.identities["code-5"] = GoogleIdentity(sub="google-ana", email="ana@lakeside.example.com")
    back = await back_from_google(harness, "code-5")
    assert back.headers["location"] == sign_in_page("signed_in")
    team = (await harness.client.get("/api/team", headers=practice.admin)).json()["members"]
    assert {m["email"]: m["status"] for m in team}["ana@lakeside.example.com"] == "active"


async def test_sign_in_is_refused_after_ten_attempts_for_one_email(harness):
    await practice_with_coder(harness)
    for _ in range(10):
        wrong = await harness.client.post("/api/auth/login", json={"email": CODER, "password": "wrong-password-0"})
        assert wrong.status_code == 401
    blocked = await harness.client.post("/api/auth/login", json={"email": CODER, "password": PASSWORD})
    assert blocked.status_code == 429
    assert blocked.json() == {"error": "rate_limited", "message": "Too many attempts. Try again in 15 minutes."}


async def test_forgot_password_is_refused_after_three_requests_an_hour(harness):
    for _ in range(3):
        assert (await harness.client.post("/api/auth/forgot", json={"email": CODER})).status_code == 204
    fourth = await harness.client.post("/api/auth/forgot", json={"email": CODER})
    assert fourth.status_code == 429
    assert fourth.json()["message"] == "Too many attempts. Try again in 60 minutes."


async def test_signed_in_devices_can_be_listed_and_signed_out(harness):
    practice = await practice_with_coder(harness)
    first = await sign_in(harness.client, CODER)
    await sign_in(harness.client, CODER)
    current = await sign_in(harness.client, CODER)
    listed = (await harness.client.get("/api/auth/sessions", headers=current)).json()
    assert len(listed) == 3
    assert [device["current"] for device in listed] == [True, False, False]
    assert set(listed[0]) == {"id", "created_at", "last_used_at", "ip", "user_agent", "current"}
    other_admin = await harness.client.delete(f"/api/auth/sessions/{listed[2]['id']}", headers=practice.admin)
    assert other_admin.status_code == 404
    ended = await harness.client.delete(f"/api/auth/sessions/{listed[2]['id']}", headers=current)
    assert ended.status_code == 204
    assert (await harness.client.get("/api/auth/me", headers=first)).status_code == 401
    fresh = await renewed(harness)
    assert len((await harness.client.get("/api/auth/sessions", headers=fresh)).json()) == 2
    assert (await harness.client.post("/api/auth/sessions/end-others", headers=fresh)).status_code == 204
    left = (await harness.client.get("/api/auth/sessions", headers=await renewed(harness))).json()
    assert [device["current"] for device in left] == [True]


async def renewed(harness) -> dict[str, str]:
    refreshed = await harness.client.post("/api/auth/refresh")
    assert refreshed.status_code == 200, refreshed.text
    return {"Authorization": f"Bearer {refreshed.json()['access_token']}"}
