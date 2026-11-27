from http.cookiejar import Cookie

import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.core.db import SessionFactory
from app.models import User, UserIdentity
from tests.builders import ADMIN_SITE, PASSWORD, Harness, back_from, create_hq_user, new_practice, sign_in

MAIN_SITE = "https://app.test"
OWNER = "owner@bodha.example.com"
LAKESIDE_ADMIN = "admin@lakeside.example.com"
SIGN_IN_FAILED = "email or password is not correct"


async def owner_with_both_accounts(harness: Harness) -> tuple[dict[str, str], dict[str, str]]:
    hq_box: dict[str, str] = {}
    practice_box: dict[str, str] = {}
    await create_hq_user(OWNER)
    hq = await sign_in(harness.client, OWNER, secret_box=hq_box, site=ADMIN_SITE)
    await new_practice(harness, name="Lakeside", admin_email=OWNER, hq_headers=hq, hq_site=ADMIN_SITE)
    return hq_box, practice_box


async def login(harness: Harness, site: str, email: str):
    return await harness.client.post(f"{site}/api/auth/login", json={"email": email, "password": PASSWORD})


def refresh_cookies(harness: Harness) -> list[Cookie]:
    return [cookie for cookie in harness.client.cookies.jar if cookie.name == "bodha_refresh"]


async def test_one_email_holds_an_hq_account_and_a_practice_account_each_on_its_own_host(harness, two_hosts):
    hq_box, practice_box = await owner_with_both_accounts(harness)
    practice = await sign_in(harness.client, OWNER, secret_box=practice_box, site=MAIN_SITE)
    hq = await sign_in(harness.client, OWNER, secret_box=hq_box, site=ADMIN_SITE)
    assert (await harness.client.get(f"{MAIN_SITE}/api/auth/me", headers=practice)).json()["role"] == "admin"
    assert (await harness.client.get(f"{ADMIN_SITE}/api/auth/me", headers=hq)).json()["role"] == "hq"
    async with SessionFactory() as db:
        rows = await db.execute(select(User.role, User.realm).where(User.email == OWNER).order_by(User.realm))
    assert rows.all() == [("hq", "hq"), ("admin", "practice")]


async def test_each_host_signs_in_only_its_own_accounts_and_refuses_the_other_hosts_tokens(harness, two_hosts):
    await create_hq_user(OWNER)
    hq = await sign_in(harness.client, OWNER, secret_box={}, site=ADMIN_SITE)
    await new_practice(harness, name="Lakeside", admin_email=LAKESIDE_ADMIN, hq_headers=hq, hq_site=ADMIN_SITE)
    practice = await sign_in(harness.client, LAKESIDE_ADMIN, secret_box={}, site=MAIN_SITE)
    for site, email in ((MAIN_SITE, OWNER), (ADMIN_SITE, LAKESIDE_ADMIN)):
        refused = await login(harness, site, email)
        assert (refused.status_code, refused.json()["message"]) == (401, SIGN_IN_FAILED)
    assert (await harness.client.get(f"{MAIN_SITE}/api/hq/overview", headers=hq)).status_code == 401
    assert (await harness.client.get(f"{ADMIN_SITE}/api/auth/me", headers=practice)).status_code == 401
    assert (await harness.client.get(f"{ADMIN_SITE}/api/hq/overview", headers=hq)).status_code == 200


async def test_session_cookies_carry_no_domain_and_never_refresh_on_the_other_host(harness, two_hosts):
    await create_hq_user(OWNER)
    await sign_in(harness.client, OWNER, secret_box={}, site=ADMIN_SITE)
    assert [(cookie.domain, cookie.domain_specified) for cookie in refresh_cookies(harness)] == [("admin.test", False)]
    refreshed = await harness.client.post(f"{ADMIN_SITE}/api/auth/refresh")
    assert refreshed.status_code == 200
    set_cookie = refreshed.headers["set-cookie"].lower()
    assert set_cookie.startswith("bodha_refresh=") and "domain=" not in set_cookie
    assert (await harness.client.post(f"{MAIN_SITE}/api/auth/refresh")).status_code == 401
    carried = harness.client.cookies.get("bodha_refresh", domain="admin.test", path="/api/auth")
    harness.client.cookies.set("bodha_refresh", carried, domain="app.test", path="/api/auth")
    assert (await harness.client.post(f"{MAIN_SITE}/api/auth/refresh")).status_code == 401
    start = await harness.client.get(f"{ADMIN_SITE}/api/auth/google/start")
    assert "domain=" not in start.headers["set-cookie"].lower()


async def test_one_google_account_links_to_the_hq_and_the_practice_account(harness, two_hosts):
    await owner_with_both_accounts(harness)
    harness.google.returns("code-1", subject="google-owner", email=OWNER)
    on_main = await back_from(harness, "google", "code-1", site=MAIN_SITE)
    on_admin = await back_from(harness, "google", "code-1", site=ADMIN_SITE)
    assert on_main.headers["location"].startswith(f"{MAIN_SITE}/sign-in#mfa=")
    assert on_admin.headers["location"].startswith(f"{ADMIN_SITE}/sign-in#mfa=")
    callbacks = [f"{MAIN_SITE}/api/auth/google/callback", f"{ADMIN_SITE}/api/auth/google/callback"]
    assert harness.google.redirects == callbacks
    assert [exchange.redirect_uri for exchange in harness.google.exchanges] == callbacks
    async with SessionFactory() as db:
        query = select(User.role, UserIdentity.realm, UserIdentity.subject).select_from(UserIdentity)
        rows = await db.execute(query.join(User, User.id == UserIdentity.user_id).order_by(UserIdentity.realm))
    assert rows.all() == [("hq", "hq", "google-owner"), ("admin", "practice", "google-owner")]


async def test_a_sign_in_started_on_one_host_cannot_finish_on_the_other(harness, two_hosts):
    await create_hq_user(OWNER)
    harness.google.returns("code-2", subject="google-owner", email=OWNER)
    start = await harness.client.get(f"{ADMIN_SITE}/api/auth/google/start")
    started = harness.client.cookies.get("bodha_oidc", domain="admin.test", path="/api/auth/google")
    harness.client.cookies.set("bodha_oidc", started, domain="app.test", path="/api/auth/google")
    state = start.headers["location"].split("state=")[1]
    back = await harness.client.get(f"{MAIN_SITE}/api/auth/google/callback", params={"code": "code-2", "state": state})
    assert back.headers["location"] == f"{MAIN_SITE}/sign-in#error=failed&provider=google"
    assert harness.google.exchanges == []


async def test_the_admin_host_never_offers_sign_up(harness, two_hosts):
    harness.google.returns("code-3", subject="google-new", email="omar@harbor.example.com")
    back = await back_from(harness, "google", "code-3", site=ADMIN_SITE)
    assert back.headers["location"] == f"{ADMIN_SITE}/sign-in#error=no_account&provider=google"
    assert (await harness.client.get(f"{ADMIN_SITE}/api/auth/providers")).json()["signup"]["enabled"] is False
    assert (await harness.client.get(f"{MAIN_SITE}/api/auth/providers")).json()["signup"]["enabled"] is True
    form = {"name": "Omar", "practice_name": "Harbor", "time_zone": "America/Chicago", "agreed": True}
    refused = await harness.client.post(f"{ADMIN_SITE}/api/signup", json={**form, "email": "omar@harbor.example.com"})
    assert refused.status_code == 404


async def test_password_reset_links_open_on_the_host_of_the_account(harness, two_hosts):
    await owner_with_both_accounts(harness)
    for site in (ADMIN_SITE, MAIN_SITE):
        sent = len(harness.messenger.sent)
        assert (await harness.client.post(f"{site}/api/auth/forgot", json={"email": OWNER})).status_code == 204
        assert len(harness.messenger.sent) == sent + 1
        assert f"{site}/set-password#" in harness.messenger.sent[-1][1]


async def test_a_practice_invite_links_to_the_main_host(harness, two_hosts):
    await create_hq_user(OWNER)
    hq = await sign_in(harness.client, OWNER, secret_box={}, site=ADMIN_SITE)
    await new_practice(harness, name="Lakeside", admin_email=LAKESIDE_ADMIN, hq_headers=hq, hq_site=ADMIN_SITE)
    invite = [body for to, body in harness.messenger.sent if to == LAKESIDE_ADMIN][0]
    assert f"{MAIN_SITE}/set-password#" in invite


@pytest.mark.parametrize(
    ("forwarded", "allowed", "hq_signs_in"),
    [("admin.test", "127.0.0.1", True), ("admin.test", "10.0.0.0/8", False), ("app.test", "127.0.0.1", False)],
)
@pytest.mark.usefixtures("two_hosts")
async def test_behind_the_web_rewrite_a_trusted_forwarded_host_picks_the_realm(
    harness, monkeypatch, forwarded, allowed, hq_signs_in
):
    monkeypatch.setattr(get_settings(), "forwarded_allow_ips", allowed)
    await create_hq_user(OWNER)
    answer = await harness.client.post(
        "http://api.internal:8000/api/auth/login",
        json={"email": OWNER, "password": PASSWORD},
        headers={"x-forwarded-host": forwarded},
    )
    assert (answer.status_code == 200) is hq_signs_in


async def test_without_an_admin_host_both_realms_share_the_main_host_and_one_email(harness):
    await create_hq_user(OWNER)
    hq = await sign_in(harness.client, OWNER, secret_box={})
    assert (await harness.client.get("/api/auth/me", headers=hq)).json()["role"] == "hq"
    taken = await harness.client.post(
        "/api/hq/practices",
        headers=hq,
        json={"name": "Lakeside", "admin_name": "Owner", "admin_email": OWNER, "plan": "professional", "seats": 5},
    )
    assert taken.status_code == 409
    await new_practice(harness, name="Lakeside", admin_email=LAKESIDE_ADMIN, hq_headers=hq)
    assert f"{MAIN_SITE}/set-password#" in harness.messenger.sent[-1][1]
    assert (await sign_in(harness.client, LAKESIDE_ADMIN, secret_box={}))["Authorization"]
    harness.google.returns("code-4", subject="google-owner", email=OWNER)
    back = await back_from(harness, "google", "code-4")
    assert back.headers["location"].startswith(f"{MAIN_SITE}/sign-in#mfa=")
    assert harness.google.redirects == [f"{MAIN_SITE}/api/auth/google/callback"]
