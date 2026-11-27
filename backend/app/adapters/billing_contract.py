from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol

from app.core.errors import AppError, Unavailable

__all__ = [
    "PAYMENT_FAILED",
    "PAYMENT_SUCCEEDED",
    "BillingProvider",
    "BillingUnavailable",
    "CheckoutRequest",
    "ProcessorEvent",
    "ProcessorSubscription",
    "SubscriptionRef",
    "WebhookRefused",
]

PAYMENT_SUCCEEDED = "succeeded"
PAYMENT_FAILED = "failed"
Payment = Literal["succeeded", "failed"]


class WebhookRefused(AppError):
    status_code = 400
    code = "bad_request"

    def __init__(self) -> None:
        super().__init__("the webhook signature is not valid")


class BillingUnavailable(Unavailable):
    def __init__(self) -> None:
        super().__init__("the payment service did not answer; try again")


@dataclass(frozen=True)
class CheckoutRequest:
    practice_id: str
    plan: str
    interval: str
    price_id: str
    quantity: int
    email: str
    customer_id: str | None
    success_url: str
    cancel_url: str


@dataclass(frozen=True)
class SubscriptionRef:
    subscription_id: str
    customer_id: str | None
    price_id: str | None


@dataclass(frozen=True)
class ProcessorEvent:
    event_id: str
    kind: str
    subscription_id: str | None
    payment: Payment | None


@dataclass(frozen=True)
class ProcessorSubscription:
    subscription_id: str
    customer_id: str | None
    practice_id: str | None
    price_id: str | None
    status: str
    current_period_end: datetime | None
    cancel_at_period_end: bool
    quantity: int


class BillingProvider(Protocol):
    name: str

    async def checkout_url(self, request: CheckoutRequest) -> str: ...

    async def manage_url(self, ref: SubscriptionRef, *, return_url: str) -> str: ...

    async def cancel_at_period_end(self, ref: SubscriptionRef) -> None: ...

    async def set_quantity(self, ref: SubscriptionRef, quantity: int) -> None: ...

    async def read_event(self, body: bytes, headers: Mapping[str, str]) -> ProcessorEvent: ...

    async def subscription(self, subscription_id: str) -> ProcessorSubscription: ...
