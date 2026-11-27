from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from app.api.blinding import SightedReader
from app.api.responses.base import ExactRoute, file_download
from app.api.responses.insights import QueryMetricsReport
from app.api.routes.billing import INSIGHT_PERIODS
from app.core.deps import Actor, Db, require
from app.core.errors import Invalid
from app.core.roles import INSIGHT_READERS
from app.models import utcnow
from app.services import query_governance, query_metrics

router = APIRouter(tags=["query governance"], route_class=ExactRoute)


@router.get("/insights/queries", response_model=QueryMetricsReport)
async def queries(
    db: Db, actor: Annotated[Actor, Depends(require(*INSIGHT_READERS))], days: int = 30
) -> dict[str, Any]:
    if days not in INSIGHT_PERIODS:
        raise Invalid(f"days must be one of {', '.join(str(period) for period in INSIGHT_PERIODS)}")
    return await query_metrics.query_metrics(db, actor.practice_id, days=days, now=utcnow())


@router.get("/notes/{note_id}/addendum.txt", **file_download("text/plain"))
async def addendum_text(note_id: str, db: Db, actor: SightedReader, request_id: str | None = None) -> Response:
    exported = await query_governance.addendum_export(db, actor, note_id, request_id=request_id)
    return Response(
        exported.text,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{exported.file_name}"'},
    )
