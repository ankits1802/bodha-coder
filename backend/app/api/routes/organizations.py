from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends

from app.adapters.billing_contract import BillingProvider
from app.api.bodies import CheckoutBody
from app.api.organization_bodies import AccessBody, CombinedBillingBody, LocationBody, OrganizationPersonBody
from app.api.responses.base import Created, ExactRoute
from app.api.responses.organizations import OrganizationInsights, OrganizationOverview, OrganizationPlan
from app.api.responses.plan import RedirectLink
from app.api.routes.billing import INSIGHT_PERIODS
from app.api.wiring import BillingProviders, Mail
from app.core.db import SessionFactory
from app.core.deps import Actor, Db, current_actor, session_actor
from app.core.errors import Invalid
from app.models import Organization
from app.services import (
    organization_insights,
    organization_people,
    organization_plan,
    organization_practices,
    organizations,
    quantity_sync,
    subscriptions,
)

router = APIRouter(prefix="/organizations/{organization_id}", tags=["organizations"], route_class=ExactRoute)


@dataclass(frozen=True)
class OrganizationSession:
    actor: Actor
    organization: Organization


async def _organization_admin(
    organization_id: str, db: Db, actor: Annotated[Actor, Depends(current_actor)]
) -> OrganizationSession:
    return OrganizationSession(actor, await organizations.organization_admin(db, actor.user, organization_id))


async def _billing_admin(
    organization_id: str, db: Db, actor: Annotated[Actor, Depends(session_actor)]
) -> OrganizationSession:
    return OrganizationSession(actor, await organizations.organization_admin(db, actor.user, organization_id))


OrganizationAdmin = Annotated[OrganizationSession, Depends(_organization_admin)]
BillingAdmin = Annotated[OrganizationSession, Depends(_billing_admin)]


async def sync_organization(billing: dict[str, BillingProvider], organization_id: str) -> None:
    async with SessionFactory() as db:
        await quantity_sync.sync_quantities(db, billing, organization_id=organization_id)


@router.get("", response_model=OrganizationOverview)
async def overview(db: Db, session: OrganizationAdmin) -> dict[str, Any]:
    return await organizations.organization_overview(db, session.organization, session.actor.user)


@router.post("/practices", response_model=Created)
async def add_practice(body: LocationBody, db: Db, session: OrganizationAdmin) -> dict[str, str]:
    location = organization_practices.Location(body.name, body.time_zone, body.agreed)
    practice = await organization_practices.add_location(db, session.actor, session.organization, location)
    return {"id": practice.id}


@router.put("/practices/{practice_id}/billing", status_code=204)
async def set_billing(
    practice_id: str,
    body: CombinedBillingBody,
    db: Db,
    session: OrganizationAdmin,
    *,
    billing: BillingProviders,
    background: BackgroundTasks,
) -> None:
    organization = session.organization
    if await organization_practices.set_practice_billing(
        db, session.actor, organization, practice_id, combined=body.combined
    ):
        background.add_task(sync_organization, billing, organization.id)


@router.post("/practices/{practice_id}/access", status_code=204)
async def grant_access(practice_id: str, body: AccessBody, db: Db, mail: Mail, session: OrganizationAdmin) -> None:
    await organization_people.grant_own_access(
        db, mail, session.actor, session.organization, practice_id, role=body.role, reason=body.reason
    )


@router.post("/people", response_model=Created)
async def add_person(body: OrganizationPersonBody, db: Db, mail: Mail, session: OrganizationAdmin) -> dict[str, str]:
    placements = [organization_people.Placement(item.practice_id, item.role) for item in body.practices]
    person = await organization_people.add_person(
        db, mail, session.actor, session.organization, name=body.name, email=str(body.email), placements=placements
    )
    return {"id": person.id}


@router.get("/insights", response_model=OrganizationInsights)
async def insights(db: Db, session: OrganizationAdmin, days: int = 30) -> dict[str, Any]:
    if days not in INSIGHT_PERIODS:
        raise Invalid(f"days must be one of {', '.join(str(period) for period in INSIGHT_PERIODS)}")
    return await organization_insights.organization_insights(db, session.organization, days=days)


@router.get("/plan", response_model=OrganizationPlan)
async def plan(db: Db, session: BillingAdmin) -> dict[str, Any]:
    return await organization_plan.organization_plan(db, session.organization)


@router.post("/plan/checkout", response_model=RedirectLink)
async def checkout(body: CheckoutBody, db: Db, session: BillingAdmin, billing: BillingProviders) -> dict[str, str]:
    choice = subscriptions.CheckoutChoice(body.plan, body.interval, body.provider)
    url = await organization_plan.start_organization_checkout(db, session.actor, session.organization, billing, choice)
    return {"url": url}


@router.post("/plan/portal", response_model=RedirectLink)
async def portal(db: Db, session: BillingAdmin, billing: BillingProviders) -> dict[str, str]:
    return {"url": await organization_plan.organization_manage_link(db, session.organization, billing)}


@router.post("/plan/cancel", status_code=204)
async def cancel(db: Db, session: BillingAdmin, billing: BillingProviders) -> None:
    await organization_plan.cancel_organization_subscription(db, session.actor, session.organization, billing)
