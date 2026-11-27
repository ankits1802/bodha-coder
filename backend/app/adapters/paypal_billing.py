from __future__ import annotations

import json
import logging
import time
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.parse import quote

import httpx

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
    "API_HOSTS",
    "HANDLED_EVENTS",
    "PAYPAL",
    "PAYPAL_STATUSES",
    "PayPalBilling",
    "PayPalConfig",
    "checkout_body",
    "event_subscription_id",
    "paypal_client",
    "subscription_state",
]

logger = logging.getLogger("bodha.billing")
PAYPAL = "paypal"
API_HOSTS = {"sandbox": "https://api-m.sandbox.paypal.com", "live": "https://api-m.paypal.com"}
AUTOPAY_PAGES = {
    "sandbox": "https://www.sandbox.paypal.com/myaccount/autopay/",
    "live": "https://www.paypal.com/myaccount/autopay/",
}
PAYPAL_STATUSES = {
    "APPROVAL_PENDING": "pending",
    "APPROVED": "pending",
    "ACTIVE": "active",
    "SUSPENDED": "past_due",
    "CANCELLED": "canceled",
    "EXPIRED": "expired",
}
SIGNATURE_HEADERS = {
    "auth_algo": "paypal-auth-algo",
    "cert_url": "paypal-cert-url",
    "transmission_id": "paypal-transmission-id",
    "transmission_sig": "paypal-transmission-sig",
    "transmission_time": "paypal-transmission-time",
}
SUBSCRIPTION_EVENTS = (
    "BILLING.SUBSCRIPTION.ACTIVATED",
    "BILLING.SUBSCRIPTION.RE-ACTIVATED",
    "BILLING.SUBSCRIPTION.UPDATED",
    "BILLING.SUBSCRIPTION.CANCELLED",
    "BILLING.SUBSCRIPTION.SUSPENDED",
    "BILLING.SUBSCRIPTION.EXPIRED",
)
SUBSCRIPTION_PAYMENT_FAILED = "BILLING.SUBSCRIPTION.PAYMENT.FAILED"
SALE_PAYMENTS = {"PAYMENT.SALE.COMPLETED": PAYMENT_SUCCEEDED, "PAYMENT.SALE.DENIED": PAYMENT_FAILED}
HANDLED_EVENTS = (*SUBSCRIPTION_EVENTS, SUBSCRIPTION_PAYMENT_FAILED, *SALE_PAYMENTS)
BRAND_NAME = "Bodha Assure"
CANCEL_REASON = "Cancelled by the practice admin"
VERIFIED = "SUCCESS"
TIMEOUT_SECONDS = 20
TOKEN_MARGIN_SECONDS = 60


@dataclass(frozen=True)
class PayPalConfig:
    client_id: str
    client_secret: str
    webhook_id: str
    environment: str


def paypal_client(environment: str) -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=API_HOSTS[environment], timeout=TIMEOUT_SECONDS)


class PayPalBilling:
    name = PAYPAL

    def __init__(self, config: PayPalConfig, client: httpx.AsyncClient) -> None:
        self._config = config
        self._client = client
        self._token: str | None = None
        self._token_until = 0.0

    async def checkout_url(self, request: CheckoutRequest) -> str:
        created = await self._send("POST", "/v1/billing/subscriptions", checkout_body(request))
        approval = _link(created, "approve")
        if approval is None:
            raise BillingUnavailable()
        return approval

    async def manage_url(self, ref: SubscriptionRef, *, return_url: str) -> str:
        return AUTOPAY_PAGES[self._config.environment]

    async def cancel_at_period_end(self, ref: SubscriptionRef) -> None:
        await self._send("POST", f"{_subscription_path(ref.subscription_id)}/cancel", {"reason": CANCEL_REASON})

    async def set_quantity(self, ref: SubscriptionRef, quantity: int) -> None:
        body = {"plan_id": ref.price_id, "quantity": str(quantity)}
        revised = await self._send("POST", f"{_subscription_path(ref.subscription_id)}/revise", body)
        if _link(revised, "approve") is not None:
            logger.warning("PayPal subscription %s needs the payer to approve a new quantity", ref.subscription_id)
            raise BillingUnavailable()

    async def read_event(self, body: bytes, headers: Mapping[str, str]) -> ProcessorEvent:
        signature = {field: headers.get(header) for field, header in SIGNATURE_HEADERS.items()}
        try:
            event = json.loads(body)
        except ValueError as error:
            raise WebhookRefused() from error
        if not all(signature.values()) or not isinstance(event, dict) or not event.get("id"):
            raise WebhookRefused()
        check = {**signature, "webhook_id": self._config.webhook_id, "webhook_event": event}
        verdict = await self._send("POST", "/v1/notifications/verify-webhook-signature", check)
        if verdict.get("verification_status") != VERIFIED:
            raise WebhookRefused()
        kind = str(event.get("event_type", ""))
        payment = SALE_PAYMENTS.get(kind) or (PAYMENT_FAILED if kind == SUBSCRIPTION_PAYMENT_FAILED else None)
        return ProcessorEvent(str(event["id"]), kind, event_subscription_id(kind, event.get("resource") or {}), payment)

    async def subscription(self, subscription_id: str) -> ProcessorSubscription:
        return subscription_state(await self._send("GET", _subscription_path(subscription_id)))

    async def _send(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {await self._access_token()}"}
        response = await self._call(self._client.build_request(method, path, json=body, headers=headers))
        return response.json() if response.content else {}

    async def _access_token(self) -> str:
        if self._token is not None and time.monotonic() < self._token_until:
            return self._token
        credentials = (self._config.client_id, self._config.client_secret)
        request = self._client.build_request("POST", "/v1/oauth2/token", data={"grant_type": "client_credentials"})
        granted = (await self._call(request, auth=credentials)).json()
        self._token = str(granted["access_token"])
        self._token_until = time.monotonic() + int(granted.get("expires_in", 0)) - TOKEN_MARGIN_SECONDS
        return self._token

    async def _call(self, request: httpx.Request, *, auth: tuple[str, str] | None = None) -> httpx.Response:
        try:
            response = await self._client.send(request, auth=auth)
            response.raise_for_status()
        except httpx.HTTPError as error:
            logger.warning("PayPal request failed (%s)", type(error).__name__)
            raise BillingUnavailable() from error
        return response


def checkout_body(request: CheckoutRequest) -> dict[str, Any]:
    return {
        "plan_id": request.price_id,
        "quantity": str(request.quantity),
        "custom_id": request.practice_id,
        "subscriber": {"email_address": request.email},
        "application_context": {
            "brand_name": BRAND_NAME,
            "user_action": "SUBSCRIBE_NOW",
            "shipping_preference": "NO_SHIPPING",
            "return_url": request.success_url,
            "cancel_url": request.cancel_url,
        },
    }


def event_subscription_id(kind: str, resource: Mapping[str, Any]) -> str | None:
    if kind in SUBSCRIPTION_EVENTS or kind == SUBSCRIPTION_PAYMENT_FAILED:
        found = resource.get("id")
    elif kind in SALE_PAYMENTS:
        found = resource.get("billing_agreement_id")
    else:
        return None
    return str(found) if found else None


def subscription_state(data: Mapping[str, Any]) -> ProcessorSubscription:
    status = str(data["status"])
    if status not in PAYPAL_STATUSES:
        raise ValueError(f"unknown PayPal subscription status {status}")
    next_billing = (data.get("billing_info") or {}).get("next_billing_time")
    return ProcessorSubscription(
        subscription_id=str(data["id"]),
        customer_id=(data.get("subscriber") or {}).get("payer_id"),
        practice_id=data.get("custom_id"),
        price_id=data.get("plan_id"),
        status=PAYPAL_STATUSES[status],
        current_period_end=datetime.fromisoformat(next_billing) if next_billing else None,
        cancel_at_period_end=status == "CANCELLED",
        quantity=int(data.get("quantity") or 1),
    )


def _subscription_path(subscription_id: str) -> str:
    return f"/v1/billing/subscriptions/{quote(subscription_id, safe='')}"


def _link(found: Mapping[str, Any], relation: str) -> str | None:
    for link in found.get("links") or []:
        if link.get("rel") == relation and link.get("href"):
            return str(link["href"])
    return None
