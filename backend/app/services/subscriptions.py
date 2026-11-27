from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.billing_contract import BillingProvider, CheckoutRequest, SubscriptionRef
from app.core.calendar import today_in, zone_named
from app.core.config import Settings, get_settings
from app.core.deps import Actor, plan_ended_on
from app.core.errors import Conflict, Invalid, NotFound
from app.models import Practice, Subscription
from app.services.audit_log import record_activity
from app.services.plan_limits import (
    active_provider_count,
    is_live,
    provider_limit,
    subscription_for,
    user_count,
    user_limit,
)
from app.services.plans import CATALOG, PlanTerms, annual_months_free, plan_terms, price_id, prices_complete

__all__ = [
    "MANAGED_BY",
    "MANAGE_ACTIONS",
    "PROVIDER_LABELS",
    "STANDINGS",
    "CheckoutChoice",
    "cancel_subscription",
    "manage_link",
    "offered_providers",
    "plan_catalog",
    "plan_overview",
    "refuse_manual_change",
    "standing",
    "start_checkout",
    "subscription_ref",
]

PLAN_PATH = "/plan"
CHECKOUT_STARTED = "checkout started"
CANCEL_REQUESTED = "subscription cancel requested"
PROVIDER_LABELS = {"stripe": "Stripe", "paypal": "PayPal"}
MANAGED_BY = {"stripe": "portal", "paypal": "cancel"}
ENDED_STATUSES = ("canceled", "expired")
STANDINGS = ("trial", "active", "past_due", "canceling", "canceled", "ended", "managed")
MANAGE_ACTIONS = ("portal", "cancel")


@dataclass(frozen=True)
class CheckoutChoice:
    plan: str
    interval: str
    provider: str


def offered_providers(providers: Mapping[str, BillingProvider], settings: Settings) -> list[str]:
    return [name for name in providers if prices_complete(settings, name)]


def plan_catalog(settings: Settings, offered: list[str]) -> dict[str, Any]:
    return {
        "plans": [_terms_view(terms) for terms in CATALOG.values()],
        "providers": offered,
        "trial_days": settings.trial_days,
    }


def standing(practice: Practice, subscription: Subscription | None) -> str:
    if subscription is not None and subscription.status == "past_due":
        return "past_due"
    if subscription is not None and is_live(subscription):
        return "canceling" if subscription.cancel_at_period_end else "active"
    if subscription is not None and subscription.status in ENDED_STATUSES:
        return "canceled"
    if plan_ended_on(practice) is not None:
        return "ended"
    return "trial" if practice.status == "trial" else "managed"


async def plan_overview(db: AsyncSession, practice: Practice) -> dict[str, Any]:
    subscription = await subscription_for(db, practice.id)
    zone = zone_named(practice.time_zone)
    trial_left = (
        (practice.renews_on - today_in(zone)).days if practice.status == "trial" and practice.renews_on else None
    )
    return {
        "plan": practice.plan,
        "standing": standing(practice, subscription),
        "renews_on": practice.renews_on.isoformat() if practice.renews_on else None,
        "trial_days_left": max(0, trial_left) if trial_left is not None else None,
        "users": await user_count(db, practice.id),
        "user_limit": user_limit(practice, subscription),
        "providers": await active_provider_count(db, practice.id),
        "provider_limit": provider_limit(practice),
        "subscription": _subscription_view(subscription, zone) if subscription else None,
    }


async def start_checkout(
    db: AsyncSession, actor: Actor, providers: Mapping[str, BillingProvider], choice: CheckoutChoice
) -> str:
    practice, settings = actor.own_practice, get_settings()
    terms = plan_terms(choice.plan)
    if not terms.self_checkout:
        raise Invalid(f"the {terms.name} plan is arranged with sales")
    chosen_price = price_id(settings, choice.provider, choice.plan, choice.interval)
    if choice.provider not in offered_providers(providers, settings) or chosen_price is None:
        raise NotFound("that payment method is not available")
    stored = await subscription_for(db, practice.id)
    if is_live(stored):
        raise Conflict("this practice already has a subscription")
    quantity = await _checkout_quantity(db, practice, terms)
    known_customer = stored.customer_id if stored is not None and stored.provider == choice.provider else None
    plan_url = f"{settings.app_url}{PLAN_PATH}"
    request = CheckoutRequest(
        practice_id=practice.id,
        plan=choice.plan,
        interval=choice.interval,
        price_id=chosen_price,
        quantity=quantity,
        email=actor.user.email,
        customer_id=known_customer,
        success_url=f"{plan_url}?checkout=done",
        cancel_url=f"{plan_url}?checkout=cancelled",
    )
    url = await providers[choice.provider].checkout_url(request)
    detail = f"{choice.provider} {choice.plan} {choice.interval}, {quantity} providers"
    record_activity(db, actor, CHECKOUT_STARTED, practice_id=practice.id, detail=detail)
    await db.commit()
    return url


async def manage_link(db: AsyncSession, actor: Actor, providers: Mapping[str, BillingProvider]) -> str:
    stored, provider = await _managed(db, actor, providers)
    return await provider.manage_url(subscription_ref(stored), return_url=f"{get_settings().app_url}{PLAN_PATH}")


async def cancel_subscription(db: AsyncSession, actor: Actor, providers: Mapping[str, BillingProvider]) -> None:
    stored, provider = await _managed(db, actor, providers)
    if not is_live(stored):
        raise Conflict("this subscription has already ended")
    if stored.cancel_at_period_end:
        raise Conflict("this subscription already ends at the end of its period")
    await provider.cancel_at_period_end(subscription_ref(stored))
    record_activity(
        db, actor, CANCEL_REQUESTED, practice_id=stored.practice_id, detail=f"{stored.provider} {stored.plan}"
    )
    await db.commit()


def subscription_ref(row: Subscription) -> SubscriptionRef:
    return SubscriptionRef(
        row.subscription_id, row.customer_id, price_id(get_settings(), row.provider, row.plan, row.interval)
    )


def refuse_manual_change(subscription: Subscription | None) -> None:
    if subscription is not None and is_live(subscription):
        label = PROVIDER_LABELS[subscription.provider]
        raise Conflict(f"this practice pays through {label}; its plan and renewal follow the subscription")


async def _checkout_quantity(db: AsyncSession, practice: Practice, terms: PlanTerms) -> int:
    active = await active_provider_count(db, practice.id)
    if terms.max_providers is not None and active > terms.max_providers:
        raise Conflict(f"the {terms.name} plan allows up to {terms.max_providers} active providers")
    return max(1, active)


async def _managed(
    db: AsyncSession, actor: Actor, providers: Mapping[str, BillingProvider]
) -> tuple[Subscription, BillingProvider]:
    stored = await subscription_for(db, actor.practice_id)
    provider = providers.get(stored.provider) if stored is not None else None
    if stored is None or provider is None:
        raise NotFound("this practice has no subscription to manage")
    return stored, provider


def _terms_view(terms: PlanTerms) -> dict[str, Any]:
    return {
        "key": terms.key,
        "pricing": terms.pricing,
        "monthly_cents": terms.monthly_cents,
        "annual_cents": terms.annual_cents,
        "annual_months_free": annual_months_free(terms),
        "max_users": terms.max_users,
        "max_providers": terms.max_providers,
    }


def _subscription_view(row: Subscription, zone: ZoneInfo) -> dict[str, Any]:
    return {
        "provider": row.provider,
        "interval": row.interval,
        "status": row.status,
        "cancel_at_period_end": row.cancel_at_period_end,
        "current_period_end": row.current_period_end.astimezone(zone).date().isoformat()
        if row.current_period_end
        else None,
        "quantity": row.quantity,
        "managed_by": MANAGED_BY[row.provider],
    }
