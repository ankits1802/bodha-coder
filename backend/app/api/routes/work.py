from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from app.core.deps import Actor, Db, require
from app.core.roles import COMPLIANCE, NOTE_READERS, PRACTICE_ROLES
from app.models import LANES
from app.services import worklists
from app.services.audit_log import record_access

router = APIRouter(tags=["work"])


@router.get("/today")
async def today(db: Db, actor: Annotated[Actor, Depends(require(*PRACTICE_ROLES))]) -> dict[str, Any]:
    summary = await worklists.today(db, actor.practice_id, actor.zone)
    if actor.user.role == "viewer":
        summary["next_up"] = []
    return summary


@router.get("/notes")
async def queue(
    *,
    db: Db,
    actor: Annotated[Actor, Depends(require(*NOTE_READERS))],
    lane: Annotated[str | None, Query(pattern="^(" + "|".join(LANES) + ")$")] = None,
    search: Annotated[str | None, Query(max_length=100)] = None,
    provider_id: str | None = None,
    batch_id: str | None = None,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    query = worklists.queue_query(
        actor.practice_id, lane=lane, search=search, provider_id=provider_id, batch_id=batch_id
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


@router.get("/compliance")
async def compliance(db: Db, actor: Annotated[Actor, Depends(require(*COMPLIANCE))]) -> dict[str, Any]:
    query = worklists.queue_query(actor.practice_id, lane="compliance", search=None, provider_id=None)
    rows = await worklists.queue_rows(db, query, offset=0)
    names = await worklists.user_names(db, {row["flagged_by"] for row in rows if row["flagged_by"]})
    for row in rows:
        row["flagged_by_name"] = names.get(row["flagged_by"] or "")
    record_access(db, actor, "listed compliance notes", detail=f"{len(rows)} rows")
    await db.commit()
    return {"items": rows, "patterns": await worklists.compliance_patterns(db, actor.practice_id)}
