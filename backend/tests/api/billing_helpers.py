from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime, time, timedelta
from itertools import count

from httpx import Response

from app.adapters.billing_contract import ProcessorSubscription
from app.core.config import get_settings
from app.services.plans import CHECKOUT_PLANS, PRICE_SETTING_PREFIX
from tests.builders import Harness, Practice, accept_invite, create_hq_user, sign_in

TODAY_UTC = datetime.now(UTC).date()
PERIOD_END = datetime.combine(TODAY_UTC + timedelta(days=60), time(18, 0), tzinfo=UTC)
LAST_PAID_DAY = PERIOD_END.date()
PROVIDER_NUMBERS = count(1)


def configure_prices(monkeypatch, *providers: str) -> None:
    for provider in providers:
        for plan in CHECKOUT_PLANS:
            for interval in ("monthly", "annual"):
                name = f"{PRICE_SETTING_PREFIX[provider]}_{plan}_{interval}"
                monkeypatch.setattr(get_settings(), name, f"{provider}-{plan}-{interval}")


async def practice_on_plan(harness: Harness, plan: str, *, seats: int = 10, name: str = "Lakeside") -> Practice:
    admin_email = f"admin@{name.lower()}.example.com"
    secrets: dict[str, str] = {}
    await create_hq_user(f"hq-{admin_email}")
    hq = await sign_in(harness.client, f"hq-{admin_email}", secret_box=secrets)
    created = await harness.client.post(
        "/api/hq/practices",
        headers=hq,
        json={"name": name, "admin_name": "Practice Admin", "admin_email": admin_email, "plan": plan, "seats": seats},
    )
    assert created.status_code == 200, created.text
    await accept_invite(harness)
    admin = await sign_in(harness.client, admin_email, secret_box=secrets)
    return Practice(created.json()["id"], admin, "", secrets)


def provider_body(*, active: bool = True) -> dict:
    number = next(PROVIDER_NUMBERS)
    return {
        "name": f"Provider {number}",
        "credential": "MD",
        "email": f"p{number}@clinic.example.com",
        "active": active,
    }


async def add_provider(harness: Harness, practice: Practice, *, active: bool = True) -> Response:
    return await harness.client.post("/api/providers", headers=practice.admin, json=provider_body(active=active))


def stripe_state(practice_id: str, **changes) -> ProcessorSubscription:
    base = ProcessorSubscription(
        subscription_id="sub_1",
        customer_id="cus_1",
        practice_id=practice_id,
        price_id="stripe-essentials-monthly",
        status="active",
        current_period_end=PERIOD_END,
        cancel_at_period_end=False,
        quantity=1,
    )
    return replace(base, **changes)


def paypal_state(practice_id: str, **changes) -> ProcessorSubscription:
    base = stripe_state(practice_id, subscription_id="I-1", customer_id="PAYER-1", price_id="paypal-essentials-monthly")
    return replace(base, **changes)


async def send_event(
    harness: Harness,
    event_id: str,
    state: ProcessorSubscription,
    *,
    provider: str = "stripe",
    payment: str | None = None,
    signature: str = "valid",
) -> Response:
    harness.billing[provider].subscriptions[state.subscription_id] = state
    body = {"id": event_id, "type": "subscription.changed", "subscription": state.subscription_id, "payment": payment}
    return await harness.client.post(
        f"/api/billing-webhooks/{provider}", content=json.dumps(body), headers={"x-test-signature": signature}
    )


async def hq_headers(harness: Harness, practice: Practice, *, name: str = "Lakeside") -> dict[str, str]:
    return await sign_in(harness.client, f"hq-admin@{name.lower()}.example.com", secret_box=practice.secrets)
