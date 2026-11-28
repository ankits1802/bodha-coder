from __future__ import annotations

from collections import Counter
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Actor
from app.models import ClaimAck, ClaimDelivery, ClaimSubmission
from app.services.audit_log import record_access
from app.services.claim_status import SENDING, latest_deliveries
from app.services.claim_submissions import claim_file_name
from app.services.worklists import count_of

__all__ = ["SUBMISSION_PAGE", "submission_page"]

SUBMISSION_PAGE = 50
LISTED = "listed claim files"


async def submission_page(db: AsyncSession, actor: Actor, offset: int) -> dict[str, Any]:
    query = select(ClaimSubmission).where(ClaimSubmission.practice_id == actor.practice_id)
    ordered = query.order_by(ClaimSubmission.created_at.desc(), ClaimSubmission.id).offset(offset)
    rows = list(await db.scalars(ordered.limit(SUBMISSION_PAGE)))
    ids = {row.id for row in rows}
    deliveries = await latest_deliveries(db, ids) if ids else {}
    claim_counts, file_outcomes = await _ack_summary(db, ids)
    items = [_view(row, deliveries.get(row.id), claim_counts, file_outcomes.get(row.id)) for row in rows]
    record_access(db, actor, LISTED, detail=f"{len(items)} rows from {offset}")
    await db.commit()
    return {"items": items, "total": await count_of(db, query), "offset": offset, "page_size": SUBMISSION_PAGE}


async def _ack_summary(db: AsyncSession, ids: set[str]) -> tuple[Counter[tuple[str, str]], dict[str, str]]:
    if not ids:
        return Counter(), {}
    counted = await db.execute(
        select(ClaimAck.submission_id, ClaimAck.outcome, func.count())
        .where(ClaimAck.submission_id.in_(ids), ClaimAck.level == "claim")
        .group_by(ClaimAck.submission_id, ClaimAck.outcome)
    )
    claim_counts: Counter[tuple[str, str]] = Counter()
    for submission_id, outcome, number in counted.tuples():
        claim_counts[(str(submission_id), outcome)] = number
    files = await db.scalars(
        select(ClaimAck)
        .where(ClaimAck.submission_id.in_(ids), ClaimAck.level == "file")
        .order_by(ClaimAck.submission_id, ClaimAck.created_at.desc())
        .distinct(ClaimAck.submission_id)
    )
    return claim_counts, {str(ack.submission_id): ack.outcome for ack in files}


def _view(
    row: ClaimSubmission,
    delivery: ClaimDelivery | None,
    claim_counts: Counter[tuple[str, str]],
    file_outcome: str | None,
) -> dict[str, Any]:
    return {
        "id": row.id,
        "at": row.created_at.isoformat(),
        "by": row.actor_name,
        "delivery": row.delivery,
        "usage": row.usage,
        "control_number": row.control_number,
        "claims": row.claims_count,
        "total_cents": row.total_cents,
        "file_name": claim_file_name(row),
        "sha256": row.file_sha256,
        "outcome": delivery.outcome if delivery else SENDING,
        "error": delivery.error if delivery else None,
        "file_ack": file_outcome,
        "accepted": claim_counts[(row.id, "accepted")],
        "rejected": claim_counts[(row.id, "rejected")],
    }
