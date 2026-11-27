from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request

from app.api.bodies import CheckoutBody
from app.api.responses.base import ExactRoute
from app.api.responses.plan import PlanCatalog, PlanStatus, RedirectLink
from app.api.wiring import BillingProviders
from app.core.config import get_settings
from app.core.deps import Actor, Db, require_for_billing
from app.core.errors import NotFound
from app.core.roles import PLAN_MANAGERS
from app.services import subscription_events, subscriptions

router = APIRouter(tags=["plan"], route_class=ExactRoute)
PlanManager = Annotated[Actor, Depends(require_for_billing(*PLAN_MANAGERS))]


@router.get("/plans", response_model=PlanCatalog)
async def plans(billing: BillingProviders) -> dict[str, Any]:
    settings = get_settings()
    return subscriptions.plan_catalog(settings, subscriptions.offered_providers(billing, settings))


@router.get("/plan", response_model=PlanStatus)
async def plan(db: Db, actor: PlanManager) -> dict[str, Any]:
    return await subscriptions.plan_overview(db, actor.own_practice)


@router.post("/plan/checkout", response_model=RedirectLink)
async def checkout(body: CheckoutBody, db: Db, actor: PlanManager, billing: BillingProviders) -> dict[str, str]:
    choice = subscriptions.CheckoutChoice(body.plan, body.interval, body.provider)
    return {"url": await subscriptions.start_checkout(db, actor, billing, choice)}


@router.post("/plan/portal", response_model=RedirectLink)
async def portal(db: Db, actor: PlanManager, billing: BillingProviders) -> dict[str, str]:
    return {"url": await subscriptions.manage_link(db, actor, billing)}


@router.post("/plan/cancel", status_code=204)
async def cancel(db: Db, actor: PlanManager, billing: BillingProviders) -> None:
    await subscriptions.cancel_subscription(db, actor, billing)


@router.post("/billing-webhooks/{provider}", status_code=204)
async def billing_webhook(provider: str, request: Request, db: Db, billing: BillingProviders) -> None:
    found = billing.get(provider)
    if found is None:
        raise NotFound("that payment provider is not set up")
    await subscription_events.receive_webhook(db, found, await request.body(), request.headers)
