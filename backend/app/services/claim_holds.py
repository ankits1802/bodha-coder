from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import LEVEL_CHANGE_PURPOSE, AddendumRequest
from app.services.claim_snapshots import latest_snapshots

__all__ = ["UNCONFIRMED_STATUSES", "held_for_confirmation"]

UNCONFIRMED_STATUSES = ("sent", "expired")


async def held_for_confirmation(db: AsyncSession, note_ids: Sequence[str]) -> set[str]:
    if not note_ids:
        return set()
    snapshots = {snapshot.id for snapshot in (await latest_snapshots(db, note_ids)).values()}
    rows = await db.execute(
        select(AddendumRequest.note_id, AddendumRequest.approved_claim_id).where(
            AddendumRequest.note_id.in_(note_ids),
            AddendumRequest.purpose == LEVEL_CHANGE_PURPOSE,
            AddendumRequest.hold_claim.is_(True),
            AddendumRequest.status.in_(UNCONFIRMED_STATUSES),
        )
    )
    return {note_id for note_id, snapshot_id in rows.all() if snapshot_id in snapshots}
