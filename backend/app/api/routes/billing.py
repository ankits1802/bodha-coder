from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from app.api.bodies import ExportBody
from app.core.deps import Actor, Db, require
from app.core.roles import BILLERS, INSIGHT_READERS
from app.models import utcnow
from app.services import billing, insights
from app.services.audit_log import record_access

router = APIRouter(tags=["billing"])
Biller = Annotated[Actor, Depends(require(*BILLERS))]


@router.get("/billing")
async def billing_list(db: Db, actor: Biller, show: Literal["ready", "exported", "all"] = "ready") -> dict[str, Any]:
    exported = {"ready": False, "exported": True, "all": None}[show]
    rows = await billing.billing_rows(db, actor.practice_id, exported=exported)
    record_access(db, actor, "listed billing", detail=f"{len(rows)} rows")
    await db.commit()
    return {"items": rows}


@router.post("/billing/export")
async def export(body: ExportBody, db: Db, actor: Biller) -> Response:
    content = await billing.export_csv(db, actor, body.note_ids)
    name = f"bodha-claims-{utcnow():%Y%m%d-%H%M}.csv"
    return Response(content, media_type="text/csv", headers={"Content-Disposition": f'attachment; filename="{name}"'})


@router.get("/insights")
async def insight(
    db: Db, actor: Annotated[Actor, Depends(require(*INSIGHT_READERS))], days: Literal[7, 14, 30, 90] = 14
) -> dict[str, Any]:
    return await insights.insights(db, actor.practice_id, days=days)
