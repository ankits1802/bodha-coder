from __future__ import annotations

import hashlib
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.object_store import ObjectStore, claim_ack_key
from app.core.config import get_settings
from app.core.deps import Actor
from app.core.errors import Invalid
from app.core.roles import BILLERS
from app.core.security import digest
from app.models import ClaimAck, ClaimAckFile, ClaimSubmission, ClaimSubmissionItem, Note, User, new_id
from app.services.ack_277 import REJECTED, BatchStatus, parse_277ca
from app.services.ack_999 import GroupAck, decoded, parse_999
from app.services.audit_log import SystemActor, record_access, record_system_access
from app.services.claim_status import latest_items
from app.services.inbox import Notice, notify
from app.services.memberships import active_members
from app.services.x12 import X12Invalid, first_transaction_code

__all__ = [
    "ACK_ACTOR",
    "ACK_RECEIVED",
    "ACK_UPLOADED",
    "CLAIM_REJECTED",
    "AckOrigin",
    "AckTally",
    "ingest_ack_file",
    "upload_ack_file",
]

ACK_ACTOR = SystemActor("bodha-clearinghouse", "Bodha (clearinghouse)")
ACK_RECEIVED = "received a clearinghouse response"
ACK_UPLOADED = "uploaded a clearinghouse response"
CLAIM_REJECTED = "claim rejected by the clearinghouse"
CONTENT_TYPE = "application/edi-x12"
REJECTION_KIND = "claim_rejected"
READERS: dict[str, Callable[[bytes], list[Any]]] = {"999": parse_999, "277": parse_277ca}


@dataclass(frozen=True)
class AckOrigin:
    practice_id: str
    source: str
    connection_id: str | None = None
    remote_name: str | None = None
    uploader: Actor | None = None


@dataclass
class AckTally:
    kind: str
    outcomes: Counter[str] = field(default_factory=Counter)
    rejected_notes: list[str] = field(default_factory=list)
    unlinked: int = 0

    def as_json(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "accepted": self.outcomes["accepted"],
            "rejected": self.outcomes["rejected"],
            "pending": self.outcomes["pending"],
            "unlinked": self.unlinked,
        }


async def upload_ack_file(db: AsyncSession, store: ObjectStore, actor: Actor, data: bytes) -> dict[str, Any]:
    limit = get_settings().max_upload_mb
    if not data:
        raise Invalid("the file is empty")
    if len(data) > limit * 1024 * 1024:
        raise Invalid(f"the file is larger than {limit} MB")
    code = first_transaction_code(decoded(data))
    if code not in READERS:
        raise Invalid("the file is not a 999 or 277CA acknowledgment")
    READERS[code](data)
    tally = await ingest_ack_file(db, store, AckOrigin(actor.practice_id, "upload", uploader=actor), data)
    await db.commit()
    return tally.as_json()


async def ingest_ack_file(db: AsyncSession, store: ObjectStore, origin: AckOrigin, data: bytes) -> AckTally:
    checksum = hashlib.sha256(data).hexdigest()
    row = ClaimAckFile(
        id=new_id(),
        practice_id=origin.practice_id,
        connection_id=origin.connection_id,
        source=origin.source,
        remote_name_sha256=digest(origin.remote_name) if origin.remote_name else None,
        file_sha256=checksum,
        file_bytes=len(data),
        uploaded_by=origin.uploader.user.id if origin.uploader else None,
    )
    earlier = await db.scalar(
        select(ClaimAckFile.file_key)
        .where(ClaimAckFile.practice_id == origin.practice_id, ClaimAckFile.file_sha256 == checksum)
        .limit(1)
    )
    tally = await _store_and_read(db, store, row, data, earlier)
    await _notify(db, origin.practice_id, tally)
    _record(db, origin, row, tally)
    return tally


async def _store_and_read(
    db: AsyncSession, store: ObjectStore, row: ClaimAckFile, data: bytes, earlier: str | None
) -> AckTally:
    if earlier is not None:
        row.kind, row.file_key = "duplicate", earlier
        db.add(row)
        return AckTally("duplicate")
    row.file_key = claim_ack_key(row.practice_id, row.id)
    await store.put(row.file_key, data, content_type=CONTENT_TYPE)
    try:
        code = first_transaction_code(decoded(data))
        parsed = READERS[code](data) if code in READERS else None
    except X12Invalid as error:
        row.kind, row.error = "unreadable", error.message[:300]
        db.add(row)
        return AckTally("unreadable")
    row.kind = {"999": "999", "277": "277CA"}.get(code, "other")
    db.add(row)
    await db.flush()
    if row.kind == "999":
        return await _record_999(db, row, parsed)
    if row.kind == "277CA":
        return await _record_277(db, row, parsed)
    return AckTally("other")


async def _record_999(db: AsyncSession, row: ClaimAckFile, groups: list[GroupAck]) -> AckTally:
    tally = AckTally("999")
    for group in groups:
        submission = await _submission_by_control(db, row.practice_id, group)
        accepted = group.accepted and all(item.accepted for item in group.sets)
        reasons = [reason.as_json() for item in group.sets for reason in item.reasons]
        reasons += [reason.as_json() for reason in group.reasons]
        outcome = "accepted" if accepted else REJECTED
        _ack(db, row, "999", "file", outcome, submission=submission, reasons=reasons)
        tally.outcomes[outcome] += 1
        tally.unlinked += submission is None
        if outcome == REJECTED and submission is not None:
            tally.rejected_notes += await _return_to_ready(db, await _submission_items(db, submission))
    return tally


async def _record_277(db: AsyncSession, row: ClaimAckFile, batches: list[BatchStatus]) -> AckTally:
    tally = AckTally("277CA")
    for batch in batches:
        submission = await _submission_by_batch(db, row.practice_id, batch.batch_ref)
        if not batch.claims:
            reasons = [line.reason().as_json() for line in batch.statuses]
            _ack(db, row, "277CA", "file", batch.outcome, submission=submission, reasons=reasons)
            tally.outcomes[batch.outcome] += 1
            if batch.outcome == REJECTED and submission is not None:
                tally.rejected_notes += await _return_to_ready(db, await _submission_items(db, submission))
            continue
        for claim in batch.claims:
            item = await _item_for(db, row.practice_id, submission, claim.claim_ref)
            reasons = [line.reason().as_json() for line in claim.statuses]
            _ack(db, row, "277CA", "claim", claim.outcome, item=item, claim=claim, reasons=reasons)
            tally.outcomes[claim.outcome] += 1
            tally.unlinked += item is None
            if claim.outcome == REJECTED and item is not None:
                tally.rejected_notes += await _return_to_ready(db, [item])
    return tally


def _ack(db: AsyncSession, row: ClaimAckFile, kind: str, level: str, outcome: str, **links: Any) -> None:
    submission, item, claim = links.get("submission"), links.get("item"), links.get("claim")
    db.add(
        ClaimAck(
            practice_id=row.practice_id,
            file_id=row.id,
            kind=kind,
            level=level,
            outcome=outcome,
            submission_id=item.submission_id if item else submission.id if submission else None,
            item_id=item.id if item else None,
            note_id=item.note_id if item else None,
            claim_ref=claim.claim_ref[:20] if claim else None,
            payer_claim_number=claim.payer_claim_number if claim else None,
            reasons=links.get("reasons") or [],
        )
    )


async def _submission_by_control(db: AsyncSession, practice_id: str, group: GroupAck) -> ClaimSubmission | None:
    if not group.group_control.isdigit():
        return None
    rows = list(
        await db.scalars(
            select(ClaimSubmission).where(
                ClaimSubmission.practice_id == practice_id,
                ClaimSubmission.control_number == int(group.group_control),
            )
        )
    )
    exact = [row for row in rows if row.sender_id == group.receiver_id.strip().upper()]
    return exact[0] if len(exact) == 1 else rows[0] if len(rows) == 1 else None


async def _submission_by_batch(db: AsyncSession, practice_id: str, batch_ref: str | None) -> ClaimSubmission | None:
    if not batch_ref:
        return None
    query = select(ClaimSubmission).where(
        ClaimSubmission.practice_id == practice_id, ClaimSubmission.batch_ref == batch_ref.strip().upper()
    )
    return await db.scalar(query)


async def _item_for(
    db: AsyncSession, practice_id: str, submission: ClaimSubmission | None, claim_ref: str
) -> ClaimSubmissionItem | None:
    query = select(ClaimSubmissionItem).where(
        ClaimSubmissionItem.practice_id == practice_id, ClaimSubmissionItem.claim_ref == claim_ref.strip().upper()
    )
    if submission is not None:
        query = query.where(ClaimSubmissionItem.submission_id == submission.id)
    return await db.scalar(query.order_by(ClaimSubmissionItem.created_at.desc()).limit(1))


async def _submission_items(db: AsyncSession, submission: ClaimSubmission) -> list[ClaimSubmissionItem]:
    query = select(ClaimSubmissionItem).where(ClaimSubmissionItem.submission_id == submission.id)
    return list((await db.scalars(query)).all())


async def _return_to_ready(db: AsyncSession, items: list[ClaimSubmissionItem]) -> list[str]:
    latest = await latest_items(db, [item.note_id for item in items])
    current = [item.note_id for item in items if latest.get(item.note_id) == item]
    notes = await db.scalars(select(Note).where(Note.id.in_(current), Note.status == "exported").with_for_update())
    for note in notes:
        note.status, note.exported_at = "approved", None
    return current


async def _notify(db: AsyncSession, practice_id: str, tally: AckTally) -> None:
    if not tally.rejected_notes:
        return
    billers = list(await db.scalars(active_members(practice_id, User.id, roles=BILLERS)))
    single = tally.rejected_notes[0] if len(tally.rejected_notes) == 1 else None
    payload = {"source": tally.kind, "claims": len(tally.rejected_notes)}
    await notify(db, practice_id, billers, Notice(REJECTION_KIND, note_id=single, payload=payload))


def _record(db: AsyncSession, origin: AckOrigin, row: ClaimAckFile, tally: AckTally) -> None:
    counts = tally.as_json()
    detail = f"{row.kind} file {row.id[:8]} · {counts['accepted']} accepted · {counts['rejected']} rejected"
    if origin.uploader is not None:
        record_access(db, origin.uploader, ACK_UPLOADED, detail=detail)
    else:
        record_system_access(db, ACK_ACTOR, origin.practice_id, ACK_RECEIVED, detail=detail)
    for note_id in tally.rejected_notes:
        record_system_access(db, ACK_ACTOR, origin.practice_id, CLAIM_REJECTED, note_id=note_id, detail=row.kind)
