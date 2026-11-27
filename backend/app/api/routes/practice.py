from __future__ import annotations

from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

from app.api.bodies import ChecksBody, ImportBody, MipsBody, PayerBody, ProviderBody, SectionBody, SecurityBody
from app.core.calendar import today_in
from app.core.deps import Actor, Db, require
from app.core.roles import ADMINS, PRACTICE_ROLES
from app.models import PlaceOfService, Provider
from app.services import payers, practice_setup, records
from app.services.provider_details import details_view

router = APIRouter(tags=["practice"])
Admin = Annotated[Actor, Depends(require(*ADMINS))]


@router.get("/practice/setup")
async def setup(db: Db, actor: Admin) -> dict[str, Any]:
    practice = actor.practice
    overview = await practice_setup.setup_overview(db, practice) if practice else {}
    return {
        **overview,
        "security": {
            "mfa_roles": practice.mfa_roles,
            "idle_minutes": practice.idle_minutes,
            "access_log_years": practice.access_log_years,
        }
        if practice
        else None,
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


@router.post("/practice/payers")
async def add_payer(body: PayerBody, db: Db, actor: Admin) -> dict[str, str]:
    payer = await payers.add_payer(db, actor, body.model_dump())
    return {"id": payer["id"]}


@router.put("/practice/payers/{payer_key}", status_code=204)
async def change_payer(payer_key: str, body: PayerBody, db: Db, actor: Admin) -> None:
    await payers.change_payer(db, actor, payer_key, body.model_dump())


@router.delete("/practice/payers/{payer_key}", status_code=204)
async def remove_payer(payer_key: str, db: Db, actor: Admin) -> None:
    await payers.remove_payer(db, actor, payer_key)


@router.get("/providers")
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


@router.post("/providers")
async def add_provider(body: ProviderBody, db: Db, actor: Admin) -> dict[str, str]:
    provider = await practice_setup.save_provider(db, actor, body.model_dump(), provider_id=None)
    return {"id": provider.id}


@router.put("/providers/{provider_id}", status_code=204)
async def edit_provider(provider_id: str, body: ProviderBody, db: Db, actor: Admin) -> None:
    await practice_setup.save_provider(db, actor, body.model_dump(), provider_id=provider_id)


@router.post("/providers/import")
async def import_providers(body: ImportBody, db: Db, actor: Admin) -> dict[str, int]:
    return {"imported": await practice_setup.import_providers(db, actor, body.csv)}


@router.get("/places")
async def places(db: Db, actor: Annotated[Actor, Depends(require(*PRACTICE_ROLES))]) -> list[dict[str, str]]:
    rows = await db.scalars(select(PlaceOfService).where(PlaceOfService.active.is_(True)).order_by(PlaceOfService.code))
    return [{"code": row.code, "name": row.name} for row in rows]


@router.get("/mips")
async def mips(db: Db, actor: Admin) -> dict[str, Any]:
    return await practice_setup.mips_overview(db, actor.practice_id)


@router.put("/mips")
async def save_mips(body: MipsBody, db: Db, actor: Admin) -> dict[str, list[str]]:
    chosen = await practice_setup.save_mips(db, actor, measure_ids=body.measure_ids, expected=body.expected_measure_ids)
    return {"measure_ids": chosen}


@router.get("/access-log")
async def access_log(
    db: Db,
    actor: Admin,
    day: date | None = None,
    user_id: str | None = None,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    return await records.access_log_page(db, actor, day=day or today_in(actor.zone), user_id=user_id, offset=offset)
