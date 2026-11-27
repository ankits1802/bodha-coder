from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy import select

from app.adapters.billing_contract import BillingProvider
from app.api.bodies import (
    ChecksBody,
    ImportBody,
    MipsBody,
    PayerBody,
    ProviderBody,
    ReviewSettingsBody,
    SectionBody,
    SecurityBody,
)
from app.api.responses.base import Created, ExactRoute
from app.api.responses.practice import (
    AccessLogPage,
    ImportedProviders,
    MipsChoice,
    MipsOverview,
    PayerOption,
    Place,
    PracticeSetup,
)
from app.api.responses.practice import Provider as ProviderView
from app.api.responses.review_records import ReviewSettings
from app.api.wiring import BillingProviders
from app.core.calendar import today_in
from app.core.db import SessionFactory
from app.core.deps import Actor, Db, require
from app.core.roles import ADMINS, PRACTICE_ROLES
from app.models import PlaceOfService, Provider
from app.services import first_run, payers, practice_setup, quantity_sync, records
from app.services.provider_details import details_view

router = APIRouter(tags=["practice"], route_class=ExactRoute)
Admin = Annotated[Actor, Depends(require(*ADMINS))]


@router.get("/practice/setup", response_model=PracticeSetup)
async def setup(db: Db, actor: Admin) -> dict[str, Any]:
    practice = actor.own_practice
    return {
        **await practice_setup.setup_overview(db, practice),
        "security": {
            "mfa_roles": practice.mfa_roles,
            "idle_minutes": practice.idle_minutes,
            "access_log_years": practice.access_log_years,
        },
        "review": practice_setup.review_settings(practice),
    }


@router.put("/practice/setup/{section}", status_code=204)
async def save_section(section: str, body: SectionBody, db: Db, actor: Admin) -> None:
    await practice_setup.save_section(db, actor, section, body.values)


@router.put("/practice/checks", status_code=204)
async def save_checks(body: ChecksBody, db: Db, actor: Admin) -> None:
    await practice_setup.save_checks(db, actor, body.checks)


@router.put("/practice/security", status_code=204)
async def save_security(body: SecurityBody, db: Db, actor: Admin) -> None:
    await practice_setup.save_security(
        db, actor, mfa_roles=body.mfa_roles, idle_minutes=body.idle_minutes, access_log_years=body.access_log_years
    )


@router.put("/practice/first-run/dismissed", status_code=204)
async def dismiss_first_run(db: Db, actor: Admin) -> None:
    await first_run.dismiss_first_run(db, actor)


@router.put("/practice/review-settings", response_model=ReviewSettings)
async def save_review_settings(body: ReviewSettingsBody, db: Db, actor: Admin) -> dict[str, bool]:
    return await practice_setup.save_review_settings(
        db, actor, confirm=body.confirm_level_changes, hold=body.hold_until_confirmed
    )


@router.get("/payers", response_model=list[PayerOption])
async def active_payers(actor: Annotated[Actor, Depends(require(*PRACTICE_ROLES))]) -> list[dict[str, Any]]:
    practice = actor.practice
    listed = payers.payer_list(practice) if practice is not None else []
    return [
        {"id": payer["id"], "name": payer["name"], "plan_type": payer.get("plan_type")}
        for payer in listed
        if payer.get("active")
    ]


@router.post("/practice/payers", response_model=Created)
async def add_payer(body: PayerBody, db: Db, actor: Admin) -> dict[str, str]:
    payer = await payers.add_payer(db, actor, body.model_dump())
    return {"id": payer["id"]}


@router.put("/practice/payers/{payer_key}", status_code=204)
async def change_payer(payer_key: str, body: PayerBody, db: Db, actor: Admin) -> None:
    await payers.change_payer(db, actor, payer_key, body.model_dump())


@router.delete("/practice/payers/{payer_key}", status_code=204)
async def remove_payer(payer_key: str, db: Db, actor: Admin) -> None:
    await payers.remove_payer(db, actor, payer_key)


@router.get("/providers", response_model=list[ProviderView])
async def providers(db: Db, actor: Annotated[Actor, Depends(require(*PRACTICE_ROLES))]) -> list[dict[str, Any]]:
    rows = await db.scalars(select(Provider).where(Provider.practice_id == actor.practice_id).order_by(Provider.name))
    return [
        {
            **{
                field: getattr(row, field)
                for field in (
                    "id",
                    "name",
                    "credential",
                    "specialty",
                    "npi",
                    "place_code",
                    "email",
                    "phone",
                    "channel",
                    "active",
                )
            },
            "details": details_view(row.details or {}),
        }
        for row in rows
    ]


def _quantity_sync(billing: BillingProviders, background: BackgroundTasks) -> Callable[[str], None]:
    return lambda practice_id: background.add_task(_sync_quantity, billing, practice_id)


SyncQuantity = Annotated[Callable[[str], None], Depends(_quantity_sync)]


@router.post("/providers", response_model=Created)
async def add_provider(body: ProviderBody, db: Db, actor: Admin, sync: SyncQuantity) -> dict[str, str]:
    provider = await practice_setup.save_provider(db, actor, body.model_dump(), provider_id=None)
    sync(actor.practice_id)
    return {"id": provider.id}


@router.put("/providers/{provider_id}", status_code=204)
async def edit_provider(provider_id: str, body: ProviderBody, db: Db, actor: Admin, sync: SyncQuantity) -> None:
    await practice_setup.save_provider(db, actor, body.model_dump(), provider_id=provider_id)
    sync(actor.practice_id)


@router.post("/providers/import", response_model=ImportedProviders)
async def import_providers(body: ImportBody, db: Db, actor: Admin, sync: SyncQuantity) -> dict[str, int]:
    imported = await practice_setup.import_providers(db, actor, body.csv)
    sync(actor.practice_id)
    return {"imported": imported}


async def _sync_quantity(billing: dict[str, BillingProvider], practice_id: str) -> None:
    async with SessionFactory() as db:
        await quantity_sync.sync_quantities(db, billing, practice_id=practice_id)


@router.get("/places", response_model=list[Place])
async def places(db: Db, actor: Annotated[Actor, Depends(require(*PRACTICE_ROLES))]) -> list[dict[str, str]]:
    rows = await db.scalars(select(PlaceOfService).where(PlaceOfService.active.is_(True)).order_by(PlaceOfService.code))
    return [{"code": row.code, "name": row.name} for row in rows]


@router.get("/mips", response_model=MipsOverview)
async def mips(db: Db, actor: Admin) -> dict[str, Any]:
    return await practice_setup.mips_overview(db, actor.practice_id)


@router.put("/mips", response_model=MipsChoice)
async def save_mips(body: MipsBody, db: Db, actor: Admin) -> dict[str, list[str]]:
    chosen = await practice_setup.save_mips(db, actor, measure_ids=body.measure_ids, expected=body.expected_measure_ids)
    return {"measure_ids": chosen}


@router.get("/access-log", response_model=AccessLogPage)
async def access_log(
    db: Db,
    actor: Admin,
    day: date | None = None,
    user_id: str | None = None,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    return await records.access_log_page(db, actor, day=day or today_in(actor.zone), user_id=user_id, offset=offset)
