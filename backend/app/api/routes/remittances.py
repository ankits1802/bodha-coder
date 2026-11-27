from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, File, Query, UploadFile
from pydantic import Field

from app.api.bodies import Body
from app.api.wiring import Store
from app.core.deps import Actor, Db, require
from app.core.roles import ADMINS, BILLERS
from app.services import remittance_views, remittances

router = APIRouter(tags=["remittances"])
Biller = Annotated[Actor, Depends(require(*BILLERS))]
Admin = Annotated[Actor, Depends(require(*ADMINS))]
LineStatus = Literal["all", "paid_as_billed", "downcoded", "denied", "matched", "unmatched"]
PlanType = Literal["commercial", "medicare", "medicaid", "other"]


class AppealDaysBody(Body):
    days: dict[PlanType, Annotated[int, Field(ge=1, le=730)]] = Field(min_length=1)


@router.post("/remittances")
async def upload(db: Db, store: Store, actor: Biller, file: Annotated[UploadFile, File()]) -> dict[str, Any]:
    uploaded = await remittances.upload_remittance(db, store, actor, file.filename or "", await file.read())
    return {"ids": uploaded.ids, "counts": uploaded.counts}


@router.get("/remittances")
async def remittance_list(db: Db, actor: Biller, offset: Annotated[int, Query(ge=0)] = 0) -> dict[str, Any]:
    return await remittance_views.remittance_page(db, actor, offset=offset)


@router.get("/remittances/appeal-days")
async def appeal_days(db: Db, actor: Biller) -> dict[str, int]:
    return await remittance_views.stored_appeal_days(db, actor)


@router.put("/remittances/appeal-days")
async def save_appeal_days(body: AppealDaysBody, db: Db, actor: Admin) -> dict[str, int]:
    return await remittance_views.save_appeal_days(db, actor, dict(body.days))


@router.get("/remittances/lines/{line_id}/appeal")
async def appeal(line_id: str, db: Db, store: Store, actor: Biller) -> dict[str, Any]:
    return await remittance_views.appeal_draft(db, store, actor, line_id)


@router.get("/remittances/{remittance_id}")
async def remittance(remittance_id: str, db: Db, actor: Biller, status: LineStatus = "all") -> dict[str, Any]:
    chosen = None if status == "all" else status
    return await remittance_views.remittance_detail(db, actor, remittance_id, status=chosen)
