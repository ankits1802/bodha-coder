from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from app.api.responses.base import ExactRoute
from app.api.responses.work import ComplianceList, QueuePage, SearchResults, TodaySummary
from app.core.deps import Actor, Db, require
from app.core.roles import COMPLIANCE, NOTE_READERS, PRACTICE_ROLES
from app.models import LANES
from app.services import worklists
from app.services.audit_log import record_access
from app.services.search import SEARCH_LIMIT, search_notes

router = APIRouter(tags=["work"], route_class=ExactRoute)
Reader = Annotated[Actor, Depends(require(*NOTE_READERS))]
ASSIGNED_FILTER = r"^(me|none|[0-9a-f-]{36})$"


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
    lane: Annotated[str | None, Query(pattern="^(" + "|".join(LANES) + ")$")] = None,
    search: Annotated[str | None, Query(max_length=100)] = None,
    provider_id: str | None = None,
    batch_id: str | None = None,
    assigned: Annotated[str | None, Query(pattern=ASSIGNED_FILTER)] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    query = worklists.queue_query(
        actor.practice_id,
        lane=lane,
        search=search,
        provider_id=provider_id,
        batch_id=batch_id,
        assigned=actor.user.id if assigned == "me" else assigned,
    )
    rows = await worklists.queue_rows(db, query, offset=offset)
    record_access(db, actor, "listed notes", detail=f"lane {lane or 'all'}, {len(rows)} rows")
    await db.commit()
    everything = worklists.queue_query(actor.practice_id, lane=None, search=None, provider_id=None)
    return {
        "items": rows,
        "lanes": await worklists.lane_counts(db, actor.practice_id),
        "total": await worklists.count_of(db, query),
        "all_total": await worklists.count_of(db, everything),
        "failed": await worklists.failed_count(db, actor.practice_id),
        "page_size": worklists.PAGE_SIZE,
    }


@router.get("/search", response_model=SearchResults)
async def find_notes(db: Db, actor: Reader, q: Annotated[str, Query(max_length=200)]) -> dict[str, Any]:
    return {"items": await search_notes(db, actor, q), "limit": SEARCH_LIMIT}


@router.get("/compliance", response_model=ComplianceList)
async def compliance(db: Db, actor: Annotated[Actor, Depends(require(*COMPLIANCE))]) -> dict[str, Any]:
    query = worklists.queue_query(actor.practice_id, lane="compliance", search=None, provider_id=None)
    rows = await worklists.queue_rows(db, query, offset=0)
    names = await worklists.user_names(db, {row["flagged_by"] for row in rows if row["flagged_by"]})
    for row in rows:
        row["flagged_by_name"] = names.get(row["flagged_by"] or "")
    record_access(db, actor, "listed compliance notes", detail=f"{len(rows)} rows")
    await db.commit()
    return {"items": rows, "patterns": await worklists.compliance_patterns(db, actor.practice_id)}
