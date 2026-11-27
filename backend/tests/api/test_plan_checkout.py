from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import update

from app.core.config import get_settings
from app.core.db import SessionFactory
from app.models import Practice
from tests.api.billing_helpers import (
    LAST_PAID_DAY,
    add_provider,
    configure_prices,
    paypal_state,
    practice_on_plan,
    send_event,
    stripe_state,
)
from tests.builders import invite_member, practice_with_provider, sign_in

CHECKOUT = {"plan": "essentials", "interval": "monthly", "provider": "stripe"}
PLAN_ROUTES = (
    ("GET", "/api/plan"),
    ("POST", "/api/plan/checkout"),
    ("POST", "/api/plan/portal"),
    ("POST", "/api/plan/cancel"),
)


async def test_the_plan_catalog_is_public_and_offers_only_fully_configured_payment_services(harness, monkeypatch):
    bare = (await harness.client.get("/api/plans")).json()
    assert (bare["providers"], bare["trial_days"]) == ([], 14)
    assert [plan["key"] for plan in bare["plans"]] == ["trial", "essentials", "professional", "enterprise"]
    essentials, professional = bare["plans"][1], bare["plans"][2]
    assert (essentials["monthly_cents"], essentials["annual_cents"], essentials["annual_months_free"]) == (
        14_900,
        149_000,
        2,
    )
    assert (professional["pricing"], professional["max_users"], professional["max_providers"]) == (
        "per_provider",
        None,
        50,
    )
    configure_prices(monkeypatch, "stripe")
    assert (await harness.client.get("/api/plans")).json()["providers"] == ["stripe"]
    configure_prices(monkeypatch, "paypal")
    assert (await harness.client.get("/api/plans")).json()["providers"] == ["stripe", "paypal"]


async def test_only_an_admin_reaches_plan_and_billing(harness, monkeypatch):
    configure_prices(monkeypatch, "stripe")
    practice = await practice_with_provider(harness)
    await invite_member(harness, practice, name="Casey Lee", email="casey@lakeside.example.com", role="coder")
    coder = await sign_in(harness.client, "casey@lakeside.example.com", secret_box=practice.secrets)
    for method, path in PLAN_ROUTES:
        body = CHECKOUT if path.endswith("checkout") else None
        response = await harness.client.request(method, path, headers=coder, json=body)
        assert response.status_code == 403, path
    assert harness.billing["stripe"].checkouts == []


async def test_checkout_bills_each_active_provider_and_returns_to_the_plan_screen(harness, monkeypatch):
    configure_prices(monkeypatch, "stripe")
    practice = await practice_with_provider(harness)
    for _ in range(2):
        assert (await add_provider(harness, practice)).status_code == 200
    assert (await add_provider(harness, practice, active=False)).status_code == 200
    body = {"plan": "professional", "interval": "annual", "provider": "stripe"}
    response = await harness.client.post("/api/plan/checkout", headers=practice.admin, json=body)
    assert response.json() == {"url": "https://pay.example.com/stripe/checkout"}
    [sent] = harness.billing["stripe"].checkouts
    assert (sent.practice_id, sent.plan, sent.interval, sent.price_id, sent.quantity) == (
        practice.id,
        "professional",
        "annual",
        "stripe-professional-annual",
        3,
    )
    plan_url = f"{get_settings().app_url}/plan"
    assert (sent.email, sent.customer_id, sent.success_url, sent.cancel_url) == (
        "admin@lakeside.example.com",
        None,
        f"{plan_url}?checkout=done",
        f"{plan_url}?checkout=cancelled",
    )
    view = (await harness.client.get("/api/plan", headers=practice.admin)).json()
    assert (view["standing"], view["subscription"]) == ("managed", None)


async def test_checkout_refuses_enterprise_an_unready_service_and_a_practice_already_paying(harness, monkeypatch):
    configure_prices(monkeypatch, "stripe")
    practice = await practice_with_provider(harness)
    enterprise = {**CHECKOUT, "plan": "enterprise"}
    paypal = {**CHECKOUT, "provider": "paypal"}
    assert (await harness.client.post("/api/plan/checkout", headers=practice.admin, json=enterprise)).status_code == 422
    assert (await harness.client.post("/api/plan/checkout", headers=practice.admin, json=paypal)).status_code == 404
    assert (await send_event(harness, "evt_1", stripe_state(practice.id))).status_code == 204
    again = await harness.client.post("/api/plan/checkout", headers=practice.admin, json=CHECKOUT)
    assert (again.status_code, again.json()["message"]) == (409, "this practice already has a subscription")


async def test_checkout_refuses_a_plan_smaller_than_the_practice(harness, monkeypatch):
    configure_prices(monkeypatch, "stripe")
    practice = await practice_with_provider(harness)
    for _ in range(3):
        assert (await add_provider(harness, practice)).status_code == 200
    refused = await harness.client.post("/api/plan/checkout", headers=practice.admin, json=CHECKOUT)
    assert (refused.status_code, refused.json()["message"]) == (
        409,
        "the Essentials plan allows up to 3 active providers",
    )


async def test_the_plan_screen_shows_trial_days_and_usage_against_the_trial_limits(harness):
    practice = await practice_on_plan(harness, "trial", seats=10)
    ends = datetime.now(ZoneInfo("America/Chicago")).date() + timedelta(days=5)
    async with SessionFactory() as db:
        await db.execute(update(Practice).where(Practice.id == practice.id).values(renews_on=ends))
        await db.commit()
    assert (await add_provider(harness, practice)).status_code == 200
    view = (await harness.client.get("/api/plan", headers=practice.admin)).json()
    assert view == {
        "plan": "trial",
        "standing": "trial",
        "renews_on": ends.isoformat(),
        "trial_days_left": 5,
        "users": 1,
        "user_limit": 5,
        "providers": 1,
        "provider_limit": 2,
        "subscription": None,
    }


async def test_a_stripe_subscriber_manages_billing_in_the_portal(harness, monkeypatch):
    configure_prices(monkeypatch, "stripe")
    practice = await practice_with_provider(harness)
    assert (await harness.client.post("/api/plan/portal", headers=practice.admin)).status_code == 404
    await send_event(harness, "evt_1", stripe_state(practice.id))
    portal = await harness.client.post("/api/plan/portal", headers=practice.admin)
    assert portal.json() == {"url": "https://pay.example.com/stripe/manage/sub_1"}
    view = (await harness.client.get("/api/plan", headers=practice.admin)).json()
    assert view["subscription"]["managed_by"] == "portal"


async def test_a_paypal_subscriber_cancels_here_and_only_the_webhook_ends_the_subscription(harness, monkeypatch):
    configure_prices(monkeypatch, "paypal")
    practice = await practice_with_provider(harness)
    await send_event(harness, "WH-1", paypal_state(practice.id), provider="paypal")
    assert (await harness.client.post("/api/plan/cancel", headers=practice.admin)).status_code == 204
    assert harness.billing["paypal"].cancelled == ["I-1"]
    view = (await harness.client.get("/api/plan", headers=practice.admin)).json()
    assert (view["standing"], view["subscription"]["managed_by"]) == ("active", "cancel")
    ended = paypal_state(practice.id, status="canceled", cancel_at_period_end=True, current_period_end=None)
    await send_event(harness, "WH-2", ended, provider="paypal")
    view = (await harness.client.get("/api/plan", headers=practice.admin)).json()
    last_day = LAST_PAID_DAY.isoformat()
    assert (view["standing"], view["renews_on"], view["subscription"]["current_period_end"]) == (
        "canceled",
        last_day,
        last_day,
    )
    assert (await harness.client.post("/api/plan/cancel", headers=practice.admin)).status_code == 409
