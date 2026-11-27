import base64
import json
from collections.abc import Callable
from datetime import UTC, datetime

import httpx
import pytest

from app.adapters.billing_contract import BillingUnavailable, CheckoutRequest, SubscriptionRef, WebhookRefused
from app.adapters.paypal_billing import API_HOSTS, PAYPAL_STATUSES, PayPalBilling, PayPalConfig, subscription_state
from app.models import SUBSCRIPTION_STATUSES

CONFIG = PayPalConfig("client-1", "secret-1", "WH-1", "sandbox")
SIGNATURE = {
    "paypal-auth-algo": "SHA256withRSA",
    "paypal-cert-url": "https://api.sandbox.paypal.com/v1/notifications/certs/CERT-1",
    "paypal-transmission-id": "tx-1",
    "paypal-transmission-sig": "sig-1",
    "paypal-transmission-time": "2026-11-27T10:00:00Z",
}
APPROVE = "https://www.sandbox.paypal.com/webapps/billing/subscriptions?ba_token=BA-1"


class PayPalSandbox:
    def __init__(self, answer: Callable[[httpx.Request], httpx.Response]) -> None:
        self.answer = answer
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if request.url.path == "/v1/oauth2/token":
            return httpx.Response(200, json={"access_token": "token-1", "expires_in": 3600})
        return self.answer(request)

    def api_calls(self) -> list[httpx.Request]:
        return [request for request in self.requests if request.url.path != "/v1/oauth2/token"]


def billing(sandbox: PayPalSandbox) -> PayPalBilling:
    client = httpx.AsyncClient(base_url=API_HOSTS["sandbox"], transport=httpx.MockTransport(sandbox))
    return PayPalBilling(CONFIG, client)


def checkout_request() -> CheckoutRequest:
    return CheckoutRequest(
        practice_id="practice-1",
        plan="professional",
        interval="monthly",
        price_id="P-PRO-M",
        quantity=3,
        email="admin@lakeside.example.com",
        customer_id=None,
        success_url="https://app.test/plan?checkout=done",
        cancel_url="https://app.test/plan?checkout=cancelled",
    )


def event_body(kind: str, resource: dict) -> bytes:
    return json.dumps({"id": "WH-EVT-1", "event_type": kind, "resource": resource}).encode()


async def test_checkout_creates_a_subscription_for_the_plan_and_provider_count_and_returns_the_approval_link():
    sandbox = PayPalSandbox(lambda request: httpx.Response(201, json={"links": [{"rel": "approve", "href": APPROVE}]}))
    url = await billing(sandbox).checkout_url(checkout_request())
    [created] = sandbox.api_calls()
    assert url == APPROVE
    assert (created.method, created.url.path, created.headers["authorization"]) == (
        "POST",
        "/v1/billing/subscriptions",
        "Bearer token-1",
    )
    assert json.loads(created.content) == {
        "plan_id": "P-PRO-M",
        "quantity": "3",
        "custom_id": "practice-1",
        "subscriber": {"email_address": "admin@lakeside.example.com"},
        "application_context": {
            "brand_name": "Bodha Assure",
            "user_action": "SUBSCRIBE_NOW",
            "shipping_preference": "NO_SHIPPING",
            "return_url": "https://app.test/plan?checkout=done",
            "cancel_url": "https://app.test/plan?checkout=cancelled",
        },
    }
    token = sandbox.requests[0]
    assert token.headers["authorization"] == "Basic " + base64.b64encode(b"client-1:secret-1").decode()


async def test_an_event_without_paypal_signature_headers_is_refused_before_asking_paypal():
    sandbox = PayPalSandbox(lambda request: httpx.Response(500))
    with pytest.raises(WebhookRefused):
        await billing(sandbox).read_event(event_body("BILLING.SUBSCRIPTION.ACTIVATED", {"id": "I-1"}), {})
    assert sandbox.requests == []


async def test_an_event_paypal_does_not_verify_is_refused():
    sandbox = PayPalSandbox(lambda request: httpx.Response(200, json={"verification_status": "FAILURE"}))
    with pytest.raises(WebhookRefused):
        await billing(sandbox).read_event(event_body("BILLING.SUBSCRIPTION.ACTIVATED", {"id": "I-1"}), SIGNATURE)


async def test_a_verified_event_is_checked_against_our_webhook_and_names_its_subscription():
    sandbox = PayPalSandbox(lambda request: httpx.Response(200, json={"verification_status": "SUCCESS"}))
    body = event_body("PAYMENT.SALE.DENIED", {"id": "SALE-1", "billing_agreement_id": "I-1"})
    event = await billing(sandbox).read_event(body, SIGNATURE)
    [check] = sandbox.api_calls()
    sent = json.loads(check.content)
    assert (check.url.path, sent["webhook_id"], sent["transmission_id"], sent["webhook_event"]["id"]) == (
        "/v1/notifications/verify-webhook-signature",
        "WH-1",
        "tx-1",
        "WH-EVT-1",
    )
    assert (event.event_id, event.subscription_id, event.payment) == ("WH-EVT-1", "I-1", "failed")


def test_a_subscription_reads_its_next_billing_time_quantity_and_practice():
    state = subscription_state(
        {
            "id": "I-1",
            "status": "ACTIVE",
            "plan_id": "P-PRO-M",
            "quantity": "3",
            "custom_id": "practice-1",
            "subscriber": {"payer_id": "PAYER-1"},
            "billing_info": {"next_billing_time": "2026-12-27T10:00:00Z"},
        }
    )
    assert state.current_period_end == datetime(2026, 12, 27, 10, tzinfo=UTC)
    assert (state.status, state.quantity, state.practice_id, state.customer_id, state.price_id) == (
        "active",
        3,
        "practice-1",
        "PAYER-1",
        "P-PRO-M",
    )


def test_a_cancelled_paypal_subscription_ends_at_its_period_end():
    state = subscription_state({"id": "I-1", "status": "CANCELLED", "plan_id": "P-PRO-M"})
    assert (state.status, state.cancel_at_period_end, state.current_period_end) == ("canceled", True, None)


def test_every_paypal_status_maps_into_the_stored_vocabulary():
    assert set(PAYPAL_STATUSES.values()) <= set(SUBSCRIPTION_STATUSES)
    assert PAYPAL_STATUSES["SUSPENDED"] == "past_due"


async def test_a_quantity_paypal_wants_the_payer_to_approve_is_retried_later():
    sandbox = PayPalSandbox(lambda request: httpx.Response(200, json={"links": [{"rel": "approve", "href": APPROVE}]}))
    with pytest.raises(BillingUnavailable):
        await billing(sandbox).set_quantity(SubscriptionRef("I-1", "PAYER-1", "P-PRO-M"), 4)
    [revise] = sandbox.api_calls()
    assert (revise.url.path, json.loads(revise.content)) == (
        "/v1/billing/subscriptions/I-1/revise",
        {"plan_id": "P-PRO-M", "quantity": "4"},
    )


async def test_a_paypal_error_becomes_unavailable_without_its_details():
    sandbox = PayPalSandbox(lambda request: httpx.Response(500, json={"name": "INTERNAL_SERVICE_ERROR"}))
    with pytest.raises(BillingUnavailable, match="did not answer"):
        await billing(sandbox).cancel_at_period_end(SubscriptionRef("I-1", "PAYER-1", "P-PRO-M"))
