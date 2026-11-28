from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ClaimAck, ClaimDelivery, ClaimSubmission, ClaimSubmissionItem

__all__ = [
    "ACCEPTED",
    "FAILED",
    "REJECTED",
    "SENDING",
    "SENT",
    "ClaimState",
    "claim_states",
    "latest_deliveries",
    "latest_items",
    "state_of",
]

SENDING, SENT, ACCEPTED, REJECTED, FAILED = "sending", "sent", "accepted", "rejected", "failed"
RESENDABLE = (REJECTED, FAILED)
STALE_SENDING = timedelta(minutes=10)
NOT_DELIVERED = {"code": "delivery", "text": "the file was not delivered to the clearinghouse"}


@dataclass(frozen=True)
class ClaimState:
    status: str
    at: datetime
    submission_id: str
    reasons: tuple[dict[str, Any], ...] = field(default=())

    @property
    def resendable(self) -> bool:
        return self.status in RESENDABLE

    def as_json(self) -> dict[str, Any]:
        return {"status": self.status, "at": self.at.isoformat(), "reasons": list(self.reasons)}


async def latest_items(db: AsyncSession, note_ids: Sequence[str]) -> dict[str, ClaimSubmissionItem]:
    if not note_ids:
        return {}
    rows = await db.scalars(
        select(ClaimSubmissionItem)
        .where(ClaimSubmissionItem.note_id.in_(note_ids))
        .order_by(ClaimSubmissionItem.note_id, ClaimSubmissionItem.created_at.desc())
        .distinct(ClaimSubmissionItem.note_id)
    )
    return {row.note_id: row for row in rows}


async def claim_states(db: AsyncSession, note_ids: Sequence[str], now: datetime) -> dict[str, ClaimState]:
    items = await latest_items(db, note_ids)
    if not items:
        return {}
    submission_ids = {item.submission_id for item in items.values()}
    submissions = {
        row.id: row for row in await db.scalars(select(ClaimSubmission).where(ClaimSubmission.id.in_(submission_ids)))
    }
    deliveries = await latest_deliveries(db, submission_ids)
    acks = await _acks(db, submission_ids, [item.id for item in items.values()])
    return {
        note_id: state_of(
            item,
            submissions[item.submission_id],
            deliveries.get(item.submission_id),
            [
                ack
                for ack in acks
                if ack.item_id == item.id or (ack.item_id is None and ack.submission_id == item.submission_id)
            ],
            now,
        )
        for note_id, item in items.items()
    }


def state_of(
    item: ClaimSubmissionItem,
    submission: ClaimSubmission,
    delivery: ClaimDelivery | None,
    acks: Sequence[ClaimAck],
    now: datetime,
) -> ClaimState:
    if delivery is None:
        stale = submission.created_at < now - STALE_SENDING
        return ClaimState(
            FAILED if stale else SENDING, submission.created_at, submission.id, (NOT_DELIVERED,) if stale else ()
        )
    if delivery.outcome == "failed":
        reason = {"code": "delivery", "text": delivery.error or NOT_DELIVERED["text"]}
        return ClaimState(FAILED, delivery.created_at, submission.id, (reason,))
    ordered = sorted(acks, key=lambda ack: ack.created_at)
    rejected = [ack for ack in ordered if ack.outcome == REJECTED]
    if rejected:
        return ClaimState(REJECTED, rejected[-1].created_at, submission.id, tuple(rejected[-1].reasons))
    claim_level = [ack for ack in ordered if ack.level == "claim" and ack.item_id == item.id]
    if claim_level and claim_level[-1].outcome == ACCEPTED:
        return ClaimState(ACCEPTED, claim_level[-1].created_at, submission.id, tuple(claim_level[-1].reasons))
    return ClaimState(SENT, delivery.created_at, submission.id)


async def latest_deliveries(db: AsyncSession, submission_ids: set[str]) -> dict[str, ClaimDelivery]:
    rows = await db.scalars(
        select(ClaimDelivery)
        .where(ClaimDelivery.submission_id.in_(submission_ids))
        .order_by(ClaimDelivery.submission_id, ClaimDelivery.created_at.desc())
        .distinct(ClaimDelivery.submission_id)
    )
    return {row.submission_id: row for row in rows}


async def _acks(db: AsyncSession, submission_ids: set[str], item_ids: list[str]) -> list[ClaimAck]:
    file_level = (ClaimAck.level == "file") & ClaimAck.submission_id.in_(submission_ids)
    rows = await db.scalars(select(ClaimAck).where(or_(file_level, ClaimAck.item_id.in_(item_ids))))
    return list(rows.all())
