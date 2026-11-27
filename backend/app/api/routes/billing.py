from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from app.api.bodies import ExportBody
from app.api.responses.base import ExactRoute, attachment, file_download
from app.api.responses.billing import BillingList
from app.api.responses.insights import Insights
from app.api.responses.review_records import ExportPage
from app.api.wiring import Store
from app.core.deps import Actor, Db, require
from app.core.errors import Invalid
from app.core.roles import BILLERS, INSIGHT_READERS
from app.services import billing, claim_exports, insights
from app.services.audit_log import record_access

router = APIRouter(tags=["billing"], route_class=ExactRoute)
INSIGHT_PERIODS = (7, 14, 30, 90)
Biller = Annotated[Actor, Depends(require(*BILLERS))]


@router.get("/billing", response_model=BillingList)
async def billing_list(
    db: Db,
    actor: Biller,
    show: Literal["ready", "exported", "all"] = "ready",
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    exported = {"ready": False, "exported": True, "all": None}[show]
    rows = await billing.billing_rows(db, actor.practice_id, exported=exported, offset=offset, limit=billing.PAGE_SIZE)
    record_access(db, actor, "listed billing", detail=f"{len(rows)} rows from {offset}")
    await db.commit()
    return {
        "items": rows,
        "summary": await billing.billing_summary(db, actor.practice_id, actor.zone),
        "total": await billing.billing_total(db, actor.practice_id, exported=exported),
        "offset": offset,
        "page_size": billing.PAGE_SIZE,
        "limit": billing.ROW_LIMIT,
    }


@router.post("/billing/export", **file_download("text/csv"))
async def export(body: ExportBody, db: Db, store: Store, actor: Biller) -> Response:
    exported = await claim_exports.export_csv(db, store, actor, body.note_ids, again=body.again)
    return attachment(exported.content, exported.media_type, exported.export.file_name)


@router.get("/billing/exports", response_model=ExportPage)
async def exports(db: Db, actor: Biller, offset: Annotated[int, Query(ge=0)] = 0) -> dict[str, Any]:
    return await claim_exports.export_page(db, actor, offset)


@router.get("/billing/exports/{export_id}/file", **file_download("application/octet-stream"))
async def export_file(export_id: str, db: Db, store: Store, actor: Biller) -> Response:
    exported = await claim_exports.stored_export(db, store, actor, export_id)
    return attachment(exported.content, exported.media_type, exported.export.file_name)


@router.get("/insights", response_model=Insights)
async def insight(
    db: Db, actor: Annotated[Actor, Depends(require(*INSIGHT_READERS))], days: int = 14
) -> dict[str, Any]:
    if days not in INSIGHT_PERIODS:
        raise Invalid(f"days must be one of {', '.join(str(period) for period in INSIGHT_PERIODS)}")
    return await insights.insights(db, actor.practice_id, days=days, time_zone=actor.zone.key)
