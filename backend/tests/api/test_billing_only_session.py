from datetime import date
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi.dependencies.utils import get_dependant
from fastapi.routing import APIRoute, iter_route_contexts
from sqlalchemy import update

from app.core.db import SessionFactory
from app.core.deps import current_actor, session_actor
from app.main import app
from app.models import Practice
from tests.api.billing_helpers import (
    LAST_PAID_DAY,
    configure_prices,
    practice_on_plan,
    provider_body,
    send_event,
    stripe_state,
)
from tests.builders import (
    PASSWORD,
    back_from_google,
    invite_member,
    pass_two_step,
    practice_with_provider,
    sign_in,
    sign_in_page,
)

ADMIN = "admin@lakeside.example.com"
CODER = "sam@lakeside.example.com"
ENDED_ON = date(2025, 12, 31)
ENDED = {"error": "plan_ended", "message": "This practice's plan ended on 2025-12-31"}
CHECKOUT = {"plan": "essentials", "interval": "monthly", "provider": "stripe"}
BILLING_SESSION_ROUTES = {
    ("GET", "/api/auth/me"),
    ("GET", "/api/auth/sessions"),
    ("DELETE", "/api/auth/sessions/{session_id}"),
    ("POST", "/api/auth/sessions/end-others"),
    ("GET", "/api/auth/recovery-codes"),
    ("POST", "/api/auth/recovery-codes"),
    ("GET", "/api/plan"),
    ("POST", "/api/plan/checkout"),
    ("POST", "/api/plan/portal"),
    ("POST", "/api/plan/cancel"),
    ("POST", "/api/auth/practice"),
    ("POST", "/api/auth/practices"),
    ("POST", "/api/auth/practices/{practice_id}/leave"),
}
REFUSED_ROUTES = (
    ("GET", "/api/today"),
    ("GET", "/api/notes"),
    ("GET", "/api/batches"),
    ("GET", "/api/billing"),
    ("GET", "/api/insights"),
    ("GET", "/api/team"),
    ("GET", "/api/providers"),
    ("GET", "/api/practice/setup"),
    ("GET", "/api/access-log"),
    ("GET", "/api/auth/preferences"),
)


async def end_plan(practice_id: str, *, status: str | None = None) -> None:
    values: dict[str, object] = {"renews_on": ENDED_ON}
    if status is not None:
        values["status"] = status
    async with SessionFactory() as db:
        await db.execute(update(Practice).where(Practice.id == practice_id).values(**values))
        await db.commit()


def _calls(dependant):
    yield dependant.call
    for child in dependant.dependencies:
        yield from _calls(child)


def billing_session_routes() -> set[tuple[str, str]]:
    found: set[tuple[str, str]] = set()
    for route in iter_route_contexts(app.routes):
        if not isinstance(route.original_route, APIRoute):
            continue
        calls = set(_calls(get_dependant(path=route.path_format, call=route.endpoint)))
        if session_actor in calls and current_actor not in calls:
            found |= {(method, route.path_format) for method in route.methods}
    return found


def test_only_account_and_plan_routes_accept_a_billing_only_session():
    assert billing_session_routes() == BILLING_SESSION_ROUTES


async def test_an_admin_of_an_ended_practice_signs_in_with_two_step_to_billing_only(harness, monkeypatch):
    configure_prices(monkeypatch, "stripe")
    practice = await practice_on_plan(harness, "trial")
    await end_plan(practice.id)
    login = await harness.client.post("/api/auth/login", json={"email": ADMIN, "password": PASSWORD})
    assert (login.status_code, login.json()["mfa"]) == (200, "verify")
    signed_in = await pass_two_step(harness.client, ADMIN, login.json()["mfa_token"], practice.secrets[ADMIN])
    assert signed_in["user"]["billing_only"] is True
    admin = {"Authorization": f"Bearer {signed_in['access_token']}"}
    me = await harness.client.get("/api/auth/me", headers=admin)
    assert (me.status_code, me.json()["billing_only"], me.json()["role"]) == (200, True, "admin")
    view = await harness.client.get("/api/plan", headers=admin)
    assert (view.status_code, view.json()["standing"], view.json()["renews_on"]) == (200, "ended", "2025-12-31")
    assert (await harness.client.get("/api/plans")).status_code == 200
    checkout = await harness.client.post("/api/plan/checkout", headers=admin, json=CHECKOUT)
    assert checkout.json() == {"url": "https://pay.example.com/stripe/checkout"}
    for path in ("/api/plan/portal", "/api/plan/cancel"):
        missing = await harness.client.post(path, headers=admin)
        assert (missing.status_code, missing.json()["message"]) == (404, "this practice has no subscription to manage")
    assert (await harness.client.get("/api/auth/sessions", headers=admin)).status_code == 200
    assert (await harness.client.get("/api/auth/recovery-codes", headers=admin)).json()["enabled"] is True
    refreshed = await harness.client.post("/api/auth/refresh")
    assert (refreshed.status_code, refreshed.json()["user"]["billing_only"]) == (200, True)
    assert (await harness.client.post("/api/auth/logout")).status_code == 204


async def test_google_and_two_step_open_a_billing_only_session_for_an_ended_admin(harness):
    practice = await practice_with_provider(harness)
    await end_plan(practice.id)
    harness.client.cookies.clear()
    harness.google.returns("code-1", subject="google-admin", email=ADMIN)
    back = await back_from_google(harness, "code-1")
    assert back.headers["location"].startswith(sign_in_page("mfa="))
    token = parse_qs(urlsplit(back.headers["location"]).fragment)["mfa"][0]
    signed_in = await pass_two_step(harness.client, ADMIN, token, practice.secrets[ADMIN])
    assert signed_in["user"]["billing_only"] is True
    refreshed = await harness.client.post("/api/auth/refresh")
    assert refreshed.json()["user"]["billing_only"] is True


async def test_a_billing_only_session_is_refused_everywhere_but_billing_and_the_account(harness):
    practice = await practice_with_provider(harness)
    assert (await harness.client.get("/api/auth/me", headers=practice.admin)).json()["billing_only"] is False
    await end_plan(practice.id)
    for method, path in REFUSED_ROUTES:
        response = await harness.client.request(method, path, headers=practice.admin)
        assert (response.status_code, response.json()) == (403, ENDED), path
    added = await harness.client.post("/api/providers", headers=practice.admin, json=provider_body())
    assert (added.status_code, added.json()) == (403, ENDED)
    assert (await harness.client.get("/api/auth/me", headers=practice.admin)).json()["billing_only"] is True
    view = await harness.client.get("/api/plan", headers=practice.admin)
    assert (view.status_code, view.json()["plan"], view.json()["standing"]) == (200, "professional", "ended")


async def test_other_roles_of_an_ended_practice_still_cannot_sign_in(harness):
    practice = await practice_with_provider(harness)
    await invite_member(harness, practice, name="Sam Patel", email=CODER, role="coder")
    coder = await sign_in(harness.client, CODER)
    await end_plan(practice.id)
    login = await harness.client.post("/api/auth/login", json={"email": CODER, "password": PASSWORD})
    assert (login.status_code, login.json()) == (403, ENDED)
    harness.google.returns("code-1", subject="google-sam", email=CODER)
    back = await back_from_google(harness, "code-1")
    assert back.headers["location"] == sign_in_page("error=plan_ended&provider=google")
    for path in ("/api/auth/me", "/api/plan", "/api/today"):
        refused = await harness.client.get(path, headers=coder)
        assert (refused.status_code, refused.json()) == (403, ENDED), path


@pytest.mark.parametrize("hq_status", ["blocked", "ended"])
async def test_a_practice_hq_blocked_or_ended_gets_no_billing_session(harness, hq_status):
    practice = await practice_with_provider(harness)
    await end_plan(practice.id, status=hq_status)
    for path in ("/api/plan", "/api/auth/me"):
        refused = await harness.client.get(path, headers=practice.admin)
        assert (refused.status_code, refused.json()["message"]) == (401, "your practice is not active"), path
    login = await harness.client.post("/api/auth/login", json={"email": ADMIN, "password": PASSWORD})
    assert (login.status_code, login.json()["message"]) == (401, "your practice is not active")
    harness.google.returns("code-1", subject="google-admin", email=ADMIN)
    back = await back_from_google(harness, "code-1")
    assert back.headers["location"] == sign_in_page("error=blocked&provider=google")


async def test_an_activating_webhook_lifts_billing_only_on_the_next_request(harness, monkeypatch):
    configure_prices(monkeypatch, "stripe")
    practice = await practice_on_plan(harness, "trial")
    await end_plan(practice.id)
    refused = await harness.client.get("/api/today", headers=practice.admin)
    assert (refused.status_code, refused.json()) == (403, ENDED)
    assert (await harness.client.post("/api/plan/checkout", headers=practice.admin, json=CHECKOUT)).status_code == 200
    assert (await send_event(harness, "evt_1", stripe_state(practice.id))).status_code == 204
    assert (await harness.client.get("/api/today", headers=practice.admin)).status_code == 200
    assert (await harness.client.get("/api/auth/me", headers=practice.admin)).json()["billing_only"] is False
    view = (await harness.client.get("/api/plan", headers=practice.admin)).json()
    assert (view["plan"], view["standing"], view["renews_on"]) == ("essentials", "active", LAST_PAID_DAY.isoformat())
    refreshed = await harness.client.post("/api/auth/refresh")
    assert refreshed.json()["user"]["billing_only"] is False
