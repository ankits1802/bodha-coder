import hashlib
import hmac
import json
import time
from datetime import UTC, datetime
from typing import Any

import pytest

from app.adapters.billing_contract import CheckoutRequest, SubscriptionRef, WebhookRefused
from app.adapters.stripe_billing import STRIPE_STATUSES, StripeBilling, event_subscription_id, subscription_state
from app.models import SUBSCRIPTION_STATUSES

SECRET = "whsec_test_only"
PERIOD_END = 1_798_761_600
INVOICE_EVENT = b'{"id": "evt_1", "type": "invoice.paid", "data": {"object": {}}}'


class RecordingStripe:
    def __init__(self, subscription: dict[str, Any] | None = None) -> None:
        self.calls: list[tuple[str, Any]] = []
        self.subscription = subscription or {}

    async def create_checkout_session(self, params: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(("checkout", params))
        return {"url": "https://checkout.stripe.com/c/pay/cs_test_1"}

    async def create_portal_session(self, params: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(("portal", params))
        return {"url": "https://billing.stripe.com/p/session/test_1"}

    async def retrieve_subscription(self, subscription_id: str) -> dict[str, Any]:
        self.calls.append(("retrieve", subscription_id))
        return self.subscription

    async def update_subscription(self, subscription_id: str, params: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(("update", (subscription_id, params)))
        return self.subscription


def request(customer_id: str | None = None) -> CheckoutRequest:
    return CheckoutRequest(
        practice_id="practice-1",
        plan="essentials",
        interval="annual",
        price_id="price_ess_y",
        quantity=3,
        email="admin@lakeside.example.com",
        customer_id=customer_id,
        success_url="https://app.test/plan?checkout=done",
        cancel_url="https://app.test/plan?checkout=cancelled",
    )


def signed(body: bytes, *, secret: str = SECRET, at: int | None = None) -> dict[str, str]:
    stamp = int(time.time()) if at is None else at
    digest = hmac.new(secret.encode(), f"{stamp}.".encode() + body, hashlib.sha256).hexdigest()
    return {"stripe-signature": f"t={stamp},v1={digest}"}


def stripe_subscription(status: str = "active", **changes: Any) -> dict[str, Any]:
    item = {"id": "si_1", "price": {"id": "price_ess_m"}, "quantity": 4, "current_period_end": PERIOD_END}
    return {
        "id": "sub_1",
        "status": status,
        "customer": "cus_1",
        "metadata": {"practice_id": "practice-1"},
        "cancel_at_period_end": False,
        "cancel_at": None,
        "items": {"data": [item]},
        **changes,
    }


async def test_checkout_asks_for_a_subscription_for_the_plan_price_and_provider_count():
    api = RecordingStripe()
    url = await StripeBilling(api, webhook_secret=SECRET).checkout_url(request())
    metadata = {"practice_id": "practice-1", "plan": "essentials", "interval": "annual"}
    assert url == "https://checkout.stripe.com/c/pay/cs_test_1"
    assert api.calls == [
        (
            "checkout",
            {
                "mode": "subscription",
                "line_items": [{"price": "price_ess_y", "quantity": 3}],
                "client_reference_id": "practice-1",
                "metadata": metadata,
                "subscription_data": {"metadata": metadata},
                "allow_promotion_codes": True,
                "success_url": "https://app.test/plan?checkout=done",
                "cancel_url": "https://app.test/plan?checkout=cancelled",
                "customer_email": "admin@lakeside.example.com",
            },
        )
    ]


async def test_a_returning_customer_is_named_instead_of_an_email():
    api = RecordingStripe()
    await StripeBilling(api, webhook_secret=SECRET).checkout_url(request(customer_id="cus_9"))
    params = api.calls[0][1]
    assert params["customer"] == "cus_9"
    assert "customer_email" not in params


async def test_a_signed_event_is_read_and_names_its_subscription():
    body = json.dumps(
        {"id": "evt_1", "type": "checkout.session.completed", "data": {"object": {"subscription": "sub_1"}}}
    )
    event = await StripeBilling(RecordingStripe(), webhook_secret=SECRET).read_event(
        body.encode(), signed(body.encode())
    )
    assert (event.event_id, event.kind, event.subscription_id, event.payment) == (
        "evt_1",
        "checkout.session.completed",
        "sub_1",
        None,
    )


@pytest.mark.parametrize(
    "headers",
    [
        {},
        signed(INVOICE_EVENT, secret="whsec_someone_else"),
        signed(INVOICE_EVENT, at=int(time.time()) - 600),
        {"stripe-signature": "not a signature"},
    ],
)
async def test_an_event_without_a_good_recent_signature_is_refused(headers):
    with pytest.raises(WebhookRefused):
        await StripeBilling(RecordingStripe(), webhook_secret=SECRET).read_event(INVOICE_EVENT, headers)


async def test_a_changed_body_breaks_the_signature():
    changed = INVOICE_EVENT.replace(b"evt_1", b"evt_2")
    with pytest.raises(WebhookRefused):
        await StripeBilling(RecordingStripe(), webhook_secret=SECRET).read_event(changed, signed(INVOICE_EVENT))


def test_an_invoice_names_its_subscription_through_its_parent():
    invoice = {"parent": {"subscription_details": {"subscription": "sub_7"}}}
    assert event_subscription_id("invoice.payment_failed", invoice) == "sub_7"
    assert event_subscription_id("customer.subscription.deleted", {"id": "sub_8"}) == "sub_8"
    assert event_subscription_id("charge.refunded", {"id": "ch_1"}) is None


def test_a_subscription_reads_its_period_end_quantity_and_price_from_its_item():
    state = subscription_state(stripe_subscription())
    assert state.current_period_end == datetime(2027, 1, 1, tzinfo=UTC)
    assert (state.price_id, state.quantity, state.customer_id, state.practice_id) == (
        "price_ess_m",
        4,
        "cus_1",
        "practice-1",
    )
    assert (state.status, state.cancel_at_period_end) == ("active", False)


@pytest.mark.parametrize(
    ("stripe_status", "ours"),
    [("trialing", "active"), ("unpaid", "past_due"), ("incomplete", "pending"), ("incomplete_expired", "expired")],
)
def test_stripe_statuses_map_to_ours(stripe_status, ours):
    assert subscription_state(stripe_subscription(stripe_status)).status == ours


def test_every_stripe_status_maps_into_the_stored_vocabulary():
    assert set(STRIPE_STATUSES.values()) <= set(SUBSCRIPTION_STATUSES)


def test_a_scheduled_cancellation_counts_as_ending_at_period_end():
    assert subscription_state(stripe_subscription(cancel_at=PERIOD_END)).cancel_at_period_end


async def test_a_new_quantity_is_prorated_on_the_subscription_item():
    api = RecordingStripe(stripe_subscription())
    await StripeBilling(api, webhook_secret=SECRET).set_quantity(SubscriptionRef("sub_1", "cus_1", "price_ess_m"), 5)
    assert api.calls[-1] == (
        "update",
        ("sub_1", {"items": [{"id": "si_1", "quantity": 5}], "proration_behavior": "create_prorations"}),
    )


async def test_cancelling_keeps_access_to_the_end_of_the_period():
    api = RecordingStripe()
    await StripeBilling(api, webhook_secret=SECRET).cancel_at_period_end(SubscriptionRef("sub_1", "cus_1", None))
    assert api.calls == [("update", ("sub_1", {"cancel_at_period_end": True}))]


async def test_the_billing_portal_opens_with_bodha_s_own_configuration_when_one_is_set() -> None:
    api = RecordingStripe()
    ref = SubscriptionRef("sub_9", "cus_9", "price_ess_m")

    await StripeBilling(api, webhook_secret=SECRET, portal_configuration="bpc_bodha").manage_url(
        ref, return_url="https://x/plan"
    )
    await StripeBilling(api, webhook_secret=SECRET).manage_url(ref, return_url="https://x/plan")

    assert api.calls == [
        ("portal", {"customer": "cus_9", "return_url": "https://x/plan", "configuration": "bpc_bodha"}),
        ("portal", {"customer": "cus_9", "return_url": "https://x/plan"}),
    ]
