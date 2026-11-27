from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.billing_contract import BillingProvider, CheckoutRequest
from app.core.calendar import today_in
from app.core.config import get_settings
from app.core.deps import Actor
from app.core.errors import Conflict, NotFound
from app.models import Organization, Practice, Subscription
from app.services.audit_log import record_activity
from app.services.organization_billing import ORGANIZATION_ZONE, combined_practices
from app.services.plan_limits import (
    active_provider_count,
    combined_provider_count,
    is_live,
    organization_subscription,
    user_count,
    user_limit,
)
from app.services.plan_notices import plan_ending_soon
from app.services.plans import TRIAL, plan_terms
from app.services.subscriptions import (
    CANCEL_REQUESTED,
    CHECKOUT_STARTED,
    CheckoutChoice,
    checkout_price,
    standing_of,
    subscription_ref,
    subscription_view,
)

__all__ = [
    "cancel_organization_subscription",
    "organization_manage_link",
    "organization_plan",
    "organization_plan_path",
    "start_organization_checkout",
]

NOTHING_COMBINED = "move a practice into combined billing first"
ALREADY_SUBSCRIBED = "this organization already has a subscription"
NO_SUBSCRIPTION = "this organization has no subscription to manage"


def organization_plan_path(organization_id: str) -> str:
    return f"/organizations/{organization_id}/plan"


async def organization_plan(db: AsyncSession, organization: Organization) -> dict[str, Any]:
    subscription = await organization_subscription(db, organization.id)
    today = today_in(ORGANIZATION_ZONE)
    ended = organization.renews_on is not None and organization.renews_on < today
    practices = await combined_practices(db, organization.id)
    return {
        "plan": organization.plan,
        "standing": standing_of(subscription, ended=ended, trial=organization.plan == TRIAL),
        "renews_on": organization.renews_on.isoformat() if organization.renews_on else None,
        "ending_soon": not is_live(subscription) and plan_ending_soon(organization.renews_on, today),
        "providers": await combined_provider_count(db, organization.id),
        "practices": [await _usage(db, practice, subscription) for practice in practices],
        "subscription": subscription_view(subscription, ORGANIZATION_ZONE) if subscription else None,
    }


async def _usage(db: AsyncSession, practice: Practice, subscription: Subscription | None) -> dict[str, Any]:
    terms = plan_terms(practice.plan)
    return {
        "id": practice.id,
        "name": practice.name,
        "status": practice.status,
        "providers": await active_provider_count(db, practice.id),
        "provider_limit": terms.max_providers,
        "users": await user_count(db, practice.id),
        "user_limit": user_limit(practice, subscription),
    }


async def start_organization_checkout(
    db: AsyncSession,
    actor: Actor,
    organization: Organization,
    providers: Mapping[str, BillingProvider],
    choice: CheckoutChoice,
) -> str:
    chosen_price = checkout_price(providers, choice)
    stored = await organization_subscription(db, organization.id)
    if is_live(stored):
        raise Conflict(ALREADY_SUBSCRIBED)
    quantity = await _checkout_quantity(db, organization, choice.plan)
    known_customer = stored.customer_id if stored is not None and stored.provider == choice.provider else None
    plan_url = f"{get_settings().app_url}{organization_plan_path(organization.id)}"
    request = CheckoutRequest(
        practice_id=None,
        organization_id=organization.id,
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
    detail = f"{organization.name}: {choice.provider} {choice.plan} {choice.interval}, {quantity} providers"
    record_activity(db, actor, CHECKOUT_STARTED, practice_id=None, detail=detail)
    await db.commit()
    return url


async def _checkout_quantity(db: AsyncSession, organization: Organization, plan: str) -> int:
    practices = await combined_practices(db, organization.id)
    if not practices:
        raise Conflict(NOTHING_COMBINED)
    terms = plan_terms(plan)
    for practice in practices:
        active = await active_provider_count(db, practice.id)
        if terms.max_providers is not None and active > terms.max_providers:
            limit = f"up to {terms.max_providers} active providers"
            raise Conflict(f"the {terms.name} plan allows {limit} in {practice.name}")
    return max(1, await combined_provider_count(db, organization.id))


async def organization_manage_link(
    db: AsyncSession, organization: Organization, providers: Mapping[str, BillingProvider]
) -> str:
    stored, provider = await _managed(db, organization, providers)
    return_url = f"{get_settings().app_url}{organization_plan_path(organization.id)}"
    return await provider.manage_url(subscription_ref(stored), return_url=return_url)


async def cancel_organization_subscription(
    db: AsyncSession, actor: Actor, organization: Organization, providers: Mapping[str, BillingProvider]
) -> None:
    stored, provider = await _managed(db, organization, providers)
    if not is_live(stored):
        raise Conflict("this subscription has already ended")
    if stored.cancel_at_period_end:
        raise Conflict("this subscription already ends at the end of its period")
    await provider.cancel_at_period_end(subscription_ref(stored))
    detail = f"{organization.name}: {stored.provider} {stored.plan}"
    record_activity(db, actor, CANCEL_REQUESTED, practice_id=None, detail=detail)
    await db.commit()


async def _managed(
    db: AsyncSession, organization: Organization, providers: Mapping[str, BillingProvider]
) -> tuple[Subscription, BillingProvider]:
    stored = await organization_subscription(db, organization.id)
    provider = providers.get(stored.provider) if stored is not None else None
    if stored is None or provider is None:
        raise NotFound(NO_SUBSCRIPTION)
    return stored, provider
