from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, select, update

from app.core.config import get_settings
from app.core.db import SessionFactory
from app.models import Activity, BillingEvent, Practice, Subscription
from app.services.subscription_events import apply_subscription
from tests.api.billing_helpers import (
    LAST_PAID_DAY,
    PERIOD_END,
    TODAY_UTC,
    configure_prices,
    hq_headers,
    practice_on_plan,
    send_event,
    stripe_state,
)

CHICAGO = ZoneInfo("America/Chicago")
FAILED_AT = datetime.combine(TODAY_UTC, time(12, 0), tzinfo=UTC)


async def stored(practice_id: str) -> tuple[Practice, Subscription | None]:
    async with SessionFactory() as db:
        practice = await db.get_one(Practice, practice_id)
        found = await db.scalar(select(Subscription).where(Subscription.practice_id == practice_id))
        return practice, found


async def count(model, *conditions) -> int:
    async with SessionFactory() as db:
        return await db.scalar(select(func.count()).select_from(model).where(*conditions)) or 0


async def apply_at(practice_id: str, now: datetime, **changes) -> None:
    async with SessionFactory() as db:
        await apply_subscription(db, "stripe", stripe_state(practice_id, **changes), payment=None, now=now)
        await db.commit()


async def test_a_webhook_with_a_bad_signature_changes_nothing(harness, monkeypatch):
    configure_prices(monkeypatch, "stripe")
    practice = await practice_on_plan(harness, "trial")
    refused = await send_event(harness, "evt_1", stripe_state(practice.id), signature="forged")
    assert (refused.status_code, refused.json()["error"]) == (400, "bad_request")
    found, subscription = await stored(practice.id)
    assert (found.plan, subscription, await count(BillingEvent)) == ("trial", None, 0)


async def test_a_webhook_for_a_payment_service_that_is_not_set_up_is_not_found(harness):
    harness.billing.pop("paypal")
    response = await harness.client.post("/api/billing-webhooks/paypal", content=b"{}")
    assert response.status_code == 404


async def test_an_active_subscription_opens_the_paid_plan_until_the_period_end(harness, monkeypatch):
    configure_prices(monkeypatch, "stripe")
    practice = await practice_on_plan(harness, "trial")
    assert (await send_event(harness, "evt_1", stripe_state(practice.id, quantity=2))).status_code == 204
    found, subscription = await stored(practice.id)
    assert (found.status, found.plan, found.renews_on) == ("active", "essentials", LAST_PAID_DAY)
    assert subscription is not None
    assert (subscription.provider, subscription.customer_id, subscription.quantity) == ("stripe", "cus_1", 2)
    view = (await harness.client.get("/api/plan", headers=practice.admin)).json()
    assert view["standing"] == "active"
    assert view["subscription"] == {
        "provider": "stripe",
        "interval": "monthly",
        "status": "active",
        "cancel_at_period_end": False,
        "current_period_end": LAST_PAID_DAY.isoformat(),
        "quantity": 2,
        "managed_by": "portal",
    }
    changes = await count(Activity, Activity.action == "subscription changed", Activity.practice_id == practice.id)
    assert changes == 1


async def test_a_repeated_event_is_applied_once(harness, monkeypatch):
    configure_prices(monkeypatch, "stripe")
    practice = await practice_on_plan(harness, "trial")
    assert (await send_event(harness, "evt_1", stripe_state(practice.id))).status_code == 204
    repeat = await send_event(harness, "evt_1", stripe_state(practice.id, status="canceled"))
    assert repeat.status_code == 204
    _, subscription = await stored(practice.id)
    assert subscription is not None and subscription.status == "active"
    assert await count(BillingEvent) == 1
    assert await count(Activity, Activity.action == "subscription changed") == 1


async def test_a_failed_payment_keeps_access_for_the_grace_days_and_payment_restores_the_period(harness, monkeypatch):
    configure_prices(monkeypatch, "stripe")
    practice = await practice_on_plan(harness, "trial")
    await send_event(harness, "evt_1", stripe_state(practice.id))
    async with SessionFactory() as db:
        failed = stripe_state(practice.id)
        await apply_subscription(db, "stripe", failed, payment="failed", now=FAILED_AT)
        await db.commit()
    found, subscription = await stored(practice.id)
    assert subscription is not None
    assert (subscription.status, subscription.past_due_since, found.renews_on) == (
        "past_due",
        FAILED_AT,
        TODAY_UTC + timedelta(days=7),
    )
    view = (await harness.client.get("/api/plan", headers=practice.admin)).json()
    assert view["standing"] == "past_due"
    await apply_at(practice.id, FAILED_AT + timedelta(days=2))
    found, subscription = await stored(practice.id)
    assert subscription is not None
    assert (subscription.status, subscription.past_due_since, found.renews_on) == ("active", None, LAST_PAID_DAY)


async def test_the_grace_days_come_from_settings(harness, monkeypatch):
    configure_prices(monkeypatch, "stripe")
    monkeypatch.setattr(get_settings(), "billing_grace_days", 3)
    practice = await practice_on_plan(harness, "trial")
    await apply_at(practice.id, FAILED_AT, status="past_due")
    found, _ = await stored(practice.id)
    assert found.renews_on == TODAY_UTC + timedelta(days=3)


async def test_a_cancelled_subscription_keeps_access_to_the_period_end_then_the_plan_ends(harness, monkeypatch):
    configure_prices(monkeypatch, "stripe")
    practice = await practice_on_plan(harness, "trial")
    await send_event(harness, "evt_1", stripe_state(practice.id))
    period_end = datetime.now(UTC) - timedelta(days=2)
    ended = stripe_state(practice.id, status="canceled", cancel_at_period_end=True, current_period_end=period_end)
    await send_event(harness, "evt_2", ended)
    found, _ = await stored(practice.id)
    last_day = period_end.astimezone(CHICAGO).date()
    assert found.renews_on == last_day
    response = await harness.client.get("/api/today", headers=practice.admin)
    assert (response.status_code, response.json()) == (
        403,
        {"error": "plan_ended", "message": f"This practice's plan ended on {last_day.isoformat()}"},
    )
    view = (await harness.client.get("/api/plan", headers=practice.admin)).json()
    assert (view["standing"], view["renews_on"]) == ("canceled", last_day.isoformat())


async def test_a_checkout_that_never_paid_leaves_the_trial_alone(harness, monkeypatch):
    configure_prices(monkeypatch, "stripe")
    practice = await practice_on_plan(harness, "trial")
    trial_end = TODAY_UTC + timedelta(days=20)
    async with SessionFactory() as db:
        await db.execute(update(Practice).where(Practice.id == practice.id).values(renews_on=trial_end))
        await db.commit()
    await send_event(harness, "evt_1", stripe_state(practice.id, status="pending"))
    await send_event(harness, "evt_2", stripe_state(practice.id, status="expired"))
    found, subscription = await stored(practice.id)
    assert (found.status, found.plan, found.renews_on) == ("trial", "trial", trial_end)
    assert subscription is not None and subscription.status == "expired"


async def test_a_subscription_never_lifts_a_block(harness, monkeypatch):
    configure_prices(monkeypatch, "stripe")
    practice = await practice_on_plan(harness, "trial")
    await send_event(harness, "evt_1", stripe_state(practice.id))
    async with SessionFactory() as db:
        await db.execute(update(Practice).where(Practice.id == practice.id).values(status="blocked"))
        await db.commit()
    later = PERIOD_END + timedelta(days=31)
    await send_event(harness, "evt_2", stripe_state(practice.id, current_period_end=later))
    found, subscription = await stored(practice.id)
    assert (found.status, found.renews_on) == ("blocked", LAST_PAID_DAY)
    assert subscription is not None and subscription.current_period_end == later


async def test_hq_cannot_change_the_plan_or_renewal_of_a_paying_practice(harness, monkeypatch):
    configure_prices(monkeypatch, "stripe")
    practice = await practice_on_plan(harness, "trial")
    hq = await hq_headers(harness, practice)
    path = f"/api/hq/practices/{practice.id}"
    await send_event(harness, "evt_1", stripe_state(practice.id))
    for change in ({"renews_on": "2030-01-01"}, {"plan": "professional"}):
        refused = await harness.client.patch(path, headers=hq, json=change)
        assert (refused.status_code, "Stripe" in refused.json()["message"]) == (409, True)
    assert (await harness.client.post(f"{path}/renew", headers=hq, json={"until": None})).status_code == 409
    assert (await harness.client.patch(path, headers=hq, json={"seats": 12})).status_code == 204
    [row] = (await harness.client.get("/api/hq/practices", headers=hq)).json()
    assert (row["plan"], row["billing_provider"], row["billing_status"], row["billing_interval"]) == (
        "essentials",
        "stripe",
        "active",
        "monthly",
    )
    await send_event(harness, "evt_2", stripe_state(practice.id, status="canceled"))
    assert (await harness.client.patch(path, headers=hq, json={"renews_on": "2030-01-01"})).status_code == 204


async def test_a_paying_practice_cannot_be_closed_until_its_subscription_ends(harness, monkeypatch):
    configure_prices(monkeypatch, "stripe")
    practice = await practice_on_plan(harness, "trial")
    hq = await hq_headers(harness, practice)
    path = f"/api/hq/practices/{practice.id}"
    await send_event(harness, "evt_1", stripe_state(practice.id))
    assert (await harness.client.patch(path, headers=hq, json={"status": "blocked"})).status_code == 204
    refused = await harness.client.post(f"{path}/close", headers=hq, json={"confirm_name": "Lakeside"})
    assert (refused.status_code, refused.json()["message"]) == (
        409,
        "cancel the practice's subscription before closing it",
    )
    await send_event(harness, "evt_2", stripe_state(practice.id, status="canceled"))
    closed = await harness.client.post(f"{path}/close", headers=hq, json={"confirm_name": "Lakeside"})
    assert closed.status_code == 204
    assert await count(Subscription) == 1
