from __future__ import annotations

from typing import Any

from fastapi import APIRouter, BackgroundTasks

from app.api.bodies import ConfirmPracticeBody, RenewBody
from app.api.organization_bodies import (
    AttachPracticeBody,
    CombinedBillingBody,
    OrganizationAdminBody,
    OrganizationBody,
    OrganizationUpdateBody,
)
from app.api.responses.base import Created, ExactRoute
from app.api.responses.hq import Renewal
from app.api.responses.organizations import HqOrganization, HqOrganizationPage, OrganizationPurged
from app.api.routes.hq import HqActor
from app.api.routes.organizations import sync_organization
from app.api.wiring import BillingProviders, Mail, Store
from app.core.deps import Db
from app.services import hq_organizations, organization_admins, organization_retention

router = APIRouter(prefix="/hq/organizations", tags=["hq"], route_class=ExactRoute)
ORGANIZATION = "/{organization_id}"


@router.get("", response_model=list[HqOrganization])
async def organizations(db: Db, actor: HqActor) -> list[dict[str, Any]]:
    return await hq_organizations.organization_rows(db)


@router.post("", response_model=Created)
async def add_organization(body: OrganizationBody, db: Db, actor: HqActor) -> dict[str, str]:
    organization = await hq_organizations.create_organization(db, actor, name=body.name, plan=body.plan)
    return {"id": organization.id}


@router.get(ORGANIZATION, response_model=HqOrganizationPage)
async def organization_page(organization_id: str, db: Db, actor: HqActor) -> dict[str, Any]:
    return await hq_organizations.organization_page(db, organization_id)


@router.patch(ORGANIZATION, status_code=204)
async def edit_organization(organization_id: str, body: OrganizationUpdateBody, db: Db, actor: HqActor) -> None:
    await hq_organizations.update_organization(db, actor, organization_id, name=body.name, plan=body.plan)


@router.post(f"{ORGANIZATION}/renew", response_model=Renewal)
async def renew(organization_id: str, body: RenewBody, db: Db, actor: HqActor) -> dict[str, str | None]:
    organization = await hq_organizations.renew_organization(db, actor, organization_id, body.until, plan=body.plan)
    renews_on = organization.renews_on
    return {"renews_on": renews_on.isoformat() if renews_on else None, "plan": organization.plan}


@router.post(f"{ORGANIZATION}/practices", status_code=204)
async def attach(organization_id: str, body: AttachPracticeBody, db: Db, actor: HqActor) -> None:
    await hq_organizations.attach_practice(db, actor, organization_id, body.practice_id)


@router.delete(f"{ORGANIZATION}/practices/{{practice_id}}", status_code=204)
async def detach(
    organization_id: str,
    practice_id: str,
    db: Db,
    actor: HqActor,
    *,
    billing: BillingProviders,
    background: BackgroundTasks,
) -> None:
    await hq_organizations.detach_practice(db, actor, organization_id, practice_id)
    background.add_task(sync_organization, billing, organization_id)


@router.put(f"{ORGANIZATION}/practices/{{practice_id}}/billing", status_code=204)
async def set_billing(
    organization_id: str,
    practice_id: str,
    body: CombinedBillingBody,
    db: Db,
    actor: HqActor,
    *,
    billing: BillingProviders,
    background: BackgroundTasks,
) -> None:
    combined = body.combined
    if await hq_organizations.set_practice_combined(db, actor, organization_id, practice_id, combined=combined):
        background.add_task(sync_organization, billing, organization_id)


@router.post(f"{ORGANIZATION}/admins", response_model=Created)
async def add_admin(
    organization_id: str, body: OrganizationAdminBody, db: Db, mail: Mail, actor: HqActor
) -> dict[str, str]:
    person = await organization_admins.add_organization_admin(
        db, mail, actor, organization_id, email=str(body.email), reason=body.reason
    )
    return {"id": person.id}


@router.delete(f"{ORGANIZATION}/admins/{{user_id}}", status_code=204)
async def remove_admin(organization_id: str, user_id: str, db: Db, actor: HqActor) -> None:
    await organization_admins.remove_organization_admin(db, actor, organization_id, user_id)


@router.post(f"{ORGANIZATION}/close", status_code=204)
async def close(organization_id: str, body: ConfirmPracticeBody, db: Db, actor: HqActor) -> None:
    await organization_retention.close_organization(db, actor, organization_id, confirm_name=body.confirm_name)


@router.post(f"{ORGANIZATION}/purge", response_model=OrganizationPurged)
async def purge(
    organization_id: str, body: ConfirmPracticeBody, db: Db, store: Store, actor: HqActor
) -> dict[str, int]:
    name = body.confirm_name
    removed = await organization_retention.purge_organization(db, store, actor, organization_id, confirm_name=name)
    return {"rows_removed": removed}
