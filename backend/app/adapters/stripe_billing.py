from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Mapping
from datetime import UTC, datetime
from typing import Any, Protocol

import stripe

from app.adapters.billing_contract import (
    PAYMENT_FAILED,
    PAYMENT_SUCCEEDED,
    BillingUnavailable,
    CheckoutRequest,
    ProcessorEvent,
    ProcessorSubscription,
    SubscriptionRef,
    WebhookRefused,
)

__all__ = [
    "HANDLED_EVENTS",
    "STRIPE",
    "STRIPE_STATUSES",
    "StripeApi",
    "StripeBilling",
    "StripeSdk",
    "checkout_params",
    "event_subscription_id",
    "subscription_state",
]

logger = logging.getLogger("bodha.billing")
STRIPE = "stripe"
SIGNATURE_HEADER = "stripe-signature"
SIGNATURE_TOLERANCE_SECONDS = 300
NETWORK_RETRIES = 2
PRORATION = "create_prorations"
CHECKOUT_COMPLETED = "checkout.session.completed"
SUBSCRIPTION_EVENTS = (
    "customer.subscription.created",
    "customer.subscription.updated",
    "customer.subscription.deleted",
)
INVOICE_PAYMENTS = {"invoice.paid": PAYMENT_SUCCEEDED, "invoice.payment_failed": PAYMENT_FAILED}
HANDLED_EVENTS = (CHECKOUT_COMPLETED, *SUBSCRIPTION_EVENTS, *INVOICE_PAYMENTS)
STRIPE_STATUSES = {
    "active": "active",
    "trialing": "active",
    "past_due": "past_due",
    "unpaid": "past_due",
    "paused": "past_due",
    "canceled": "canceled",
    "incomplete": "pending",
    "incomplete_expired": "expired",
}


class StripeApi(Protocol):
    async def create_checkout_session(self, params: dict[str, Any]) -> dict[str, Any]: ...

    async def create_portal_session(self, params: dict[str, Any]) -> dict[str, Any]: ...

    async def retrieve_subscription(self, subscription_id: str) -> dict[str, Any]: ...

    async def update_subscription(self, subscription_id: str, params: dict[str, Any]) -> dict[str, Any]: ...


class StripeSdk:
    def __init__(self, secret_key: str) -> None:
        self._client = stripe.StripeClient(
            secret_key, http_client=stripe.HTTPXClient(), max_network_retries=NETWORK_RETRIES
        )

    async def create_checkout_session(self, params: dict[str, Any]) -> dict[str, Any]:
        return await _plain(self._client.v1.checkout.sessions.create_async(params))

    async def create_portal_session(self, params: dict[str, Any]) -> dict[str, Any]:
        return await _plain(self._client.v1.billing_portal.sessions.create_async(params))

    async def retrieve_subscription(self, subscription_id: str) -> dict[str, Any]:
        return await _plain(self._client.v1.subscriptions.retrieve_async(subscription_id))

    async def update_subscription(self, subscription_id: str, params: dict[str, Any]) -> dict[str, Any]:
        return await _plain(self._client.v1.subscriptions.update_async(subscription_id, params))


class StripeBilling:
    name = STRIPE

    def __init__(self, api: StripeApi, *, webhook_secret: str, portal_configuration: str | None = None) -> None:
        self._api = api
        self._webhook_secret = webhook_secret
        self._portal_configuration = portal_configuration

    async def checkout_url(self, request: CheckoutRequest) -> str:
        session = await self._api.create_checkout_session(checkout_params(request))
        return str(session["url"])

    async def manage_url(self, ref: SubscriptionRef, *, return_url: str) -> str:
        params = {"customer": ref.customer_id, "return_url": return_url}
        if self._portal_configuration:
            params["configuration"] = self._portal_configuration
        portal = await self._api.create_portal_session(params)
        return str(portal["url"])

    async def cancel_at_period_end(self, ref: SubscriptionRef) -> None:
        await self._api.update_subscription(ref.subscription_id, {"cancel_at_period_end": True})

    async def set_quantity(self, ref: SubscriptionRef, quantity: int) -> None:
        item = _first_item(await self._api.retrieve_subscription(ref.subscription_id))
        if item is None:
            raise BillingUnavailable()
        await self._api.update_subscription(
            ref.subscription_id,
            {"items": [{"id": item["id"], "quantity": quantity}], "proration_behavior": PRORATION},
        )

    async def read_event(self, body: bytes, headers: Mapping[str, str]) -> ProcessorEvent:
        try:
            stripe.WebhookSignature.verify_header(
                body, headers.get(SIGNATURE_HEADER), self._webhook_secret, tolerance=SIGNATURE_TOLERANCE_SECONDS
            )
            event = json.loads(body)
        except (stripe.SignatureVerificationError, ValueError) as error:
            raise WebhookRefused() from error
        kind = str(event["type"])
        subscription_id = event_subscription_id(kind, event["data"]["object"])
        return ProcessorEvent(str(event["id"]), kind, subscription_id, INVOICE_PAYMENTS.get(kind))

    async def subscription(self, subscription_id: str) -> ProcessorSubscription:
        return subscription_state(await self._api.retrieve_subscription(subscription_id))


def checkout_params(request: CheckoutRequest) -> dict[str, Any]:
    metadata = {"practice_id": request.practice_id, "plan": request.plan, "interval": request.interval}
    customer = {"customer": request.customer_id} if request.customer_id else {"customer_email": request.email}
    return {
        "mode": "subscription",
        "line_items": [{"price": request.price_id, "quantity": request.quantity}],
        "client_reference_id": request.practice_id,
        "metadata": metadata,
        "subscription_data": {"metadata": metadata},
        "allow_promotion_codes": True,
        "success_url": request.success_url,
        "cancel_url": request.cancel_url,
        **customer,
    }


def event_subscription_id(kind: str, found: Mapping[str, Any]) -> str | None:
    if kind == CHECKOUT_COMPLETED:
        return _id_of(found.get("subscription"))
    if kind in SUBSCRIPTION_EVENTS:
        return _id_of(found.get("id"))
    if kind in INVOICE_PAYMENTS:
        details = (found.get("parent") or {}).get("subscription_details") or {}
        return _id_of(details.get("subscription") or found.get("subscription"))
    return None


def subscription_state(data: Mapping[str, Any]) -> ProcessorSubscription:
    status = str(data["status"])
    if status not in STRIPE_STATUSES:
        raise ValueError(f"unknown Stripe subscription status {status}")
    item = _first_item(data) or {}
    period_end = item.get("current_period_end") or data.get("current_period_end")
    return ProcessorSubscription(
        subscription_id=str(data["id"]),
        customer_id=_id_of(data.get("customer")),
        practice_id=(data.get("metadata") or {}).get("practice_id"),
        price_id=_id_of(item.get("price")),
        status=STRIPE_STATUSES[status],
        current_period_end=datetime.fromtimestamp(int(period_end), UTC) if period_end else None,
        cancel_at_period_end=bool(data.get("cancel_at_period_end") or data.get("cancel_at")),
        quantity=int(item.get("quantity") or 1),
    )


def _first_item(data: Mapping[str, Any]) -> Mapping[str, Any] | None:
    items = (data.get("items") or {}).get("data") or []
    return items[0] if items else None


def _id_of(value: Any) -> str | None:
    if isinstance(value, Mapping):
        value = value.get("id")
    return str(value) if value else None


async def _plain(call: Awaitable[stripe.StripeObject]) -> dict[str, Any]:
    try:
        found = await call
    except stripe.StripeError as error:
        logger.warning("Stripe request failed (%s)", type(error).__name__)
        raise BillingUnavailable() from error
    return found.to_dict()
