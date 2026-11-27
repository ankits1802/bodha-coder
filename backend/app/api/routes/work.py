from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from app.api.bodies import QueueViewBody
from app.api.responses.base import ExactRoute, Lane
from app.api.responses.work import (
    ComplianceList,
    LaneReason,
    QueuePage,
    QueueSort,
    QueueViews,
    SavedView,
    SearchResults,
    TodaySummary,
)
from app.core.deps import Actor, Db, require
from app.core.roles import COMPLIANCE, NOTE_READERS, PRACTICE_ROLES
from app.services import queue_views, worklists
from app.services.audit_log import record_access
from app.services.search import SEARCH_LIMIT, search_notes
from app.services.worklists import ASSIGNED_PATTERN, DUE_SORT, QueueFilter

router = APIRouter(tags=["work"], route_class=ExactRoute)
Reader = Annotated[Actor, Depends(require(*NOTE_READERS))]


@router.get("/today", response_model=TodaySummary)
async def today(db: Db, actor: Annotated[Actor, Depends(require(*PRACTICE_ROLES))]) -> dict[str, Any]:
    summary = await worklists.today(db, actor.practice_id, actor.zone)
    if actor.role == "viewer":
        summary["next_up"] = []
    return summary


@router.get("/notes", response_model=QueuePage)
async def queue(
    *,
    db: Db,
    actor: Reader,
    lane: Lane | None = None,
    reason: LaneReason | None = None,
    search: Annotated[str | None, Query(max_length=100)] = None,
    provider_id: str | None = None,
    batch_id: str | None = None,
    assigned: Annotated[str | None, Query(pattern=ASSIGNED_PATTERN)] = None,
    overdue: bool = False,
    sort: QueueSort = DUE_SORT,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    wanted = QueueFilter(
        lane=lane,
        reason=reason,
        search=search,
        provider_id=provider_id,
        batch_id=batch_id,
        assigned=actor.user.id if assigned == "me" else assigned,
        overdue=overdue,
        sort=sort,
    )
    query = worklists.queue_query(actor.practice_id, wanted)
    rows = await worklists.queue_rows(db, query, offset=offset)
    record_access(db, actor, "listed notes", detail=f"lane {lane or 'all'}, {len(rows)} rows")
    await db.commit()
    return {
        "items": rows,
        "lanes": await worklists.lane_counts(db, actor.practice_id),
        "provider_reasons": await worklists.provider_reason_counts(db, actor.practice_id),
        "total": await worklists.count_of(db, query),
        "all_total": await worklists.count_of(db, worklists.queue_query(actor.practice_id, QueueFilter())),
        "failed": await worklists.failed_count(db, actor.practice_id),
        "page_size": worklists.PAGE_SIZE,
    }


@router.get("/queue-views", response_model=QueueViews)
async def views(db: Db, actor: Reader) -> dict[str, Any]:
    return await queue_views.queue_views(db, actor)


@router.post("/queue-views", response_model=SavedView)
async def save_view(body: QueueViewBody, db: Db, actor: Reader) -> dict[str, Any]:
    return await queue_views.save_view(db, actor, body.name, body.filters.model_dump())


@router.delete("/queue-views/{view_id}", status_code=204)
async def delete_view(view_id: str, db: Db, actor: Reader) -> None:
    await queue_views.delete_view(db, actor, view_id)


@router.get("/search", response_model=SearchResults)
async def find_notes(db: Db, actor: Reader, q: Annotated[str, Query(max_length=200)]) -> dict[str, Any]:
    return {"items": await search_notes(db, actor, q), "limit": SEARCH_LIMIT}


@router.get("/compliance", response_model=ComplianceList)
async def compliance(db: Db, actor: Annotated[Actor, Depends(require(*COMPLIANCE))]) -> dict[str, Any]:
    query = worklists.queue_query(actor.practice_id, QueueFilter(lane="compliance"))
    rows = await worklists.queue_rows(db, query, offset=0)
    names = await worklists.user_names(db, {row["flagged_by"] for row in rows if row["flagged_by"]})
    for row in rows:
        row["flagged_by_name"] = names.get(row["flagged_by"] or "")
    record_access(db, actor, "listed compliance notes", detail=f"{len(rows)} rows")
    await db.commit()
    return {"items": rows, "patterns": await worklists.compliance_patterns(db, actor.practice_id)}
