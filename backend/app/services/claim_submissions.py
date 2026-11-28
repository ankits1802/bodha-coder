from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.object_store import ObjectStore, claim_file_key
from app.adapters.sftp import FileLink, LinkRefused
from app.core.deps import Actor
from app.core.errors import Conflict, Invalid, NotFound
from app.models import ClaimDelivery, ClaimSubmission, ClaimSubmissionItem, ClearinghouseConnection, new_id, utcnow
from app.services.audit_log import record_access
from app.services.claim_837 import IMPLEMENTATION, ClaimFile, ProfessionalClaim, Receiver, Submitter, write_837p
from app.services.claim_837_check import check_837p
from app.services.claim_assembly import professional_claim
from app.services.claim_exports import mark_exported
from app.services.claim_ready import ReadyClaims, ready_claims
from app.services.clearinghouse_settings import current_connection, sftp_target
from app.services.x12_writer import Interchange

__all__ = [
    "CLAIM_CONTENT_TYPE",
    "CLAIMS_DOWNLOADED",
    "CLAIMS_NOT_SENT",
    "CLAIMS_SENT",
    "ClaimFileOut",
    "claim_file_name",
    "download_claims",
    "send_claims",
    "stored_claim_file",
]

CLAIM_CONTENT_TYPE = "application/edi-x12"
CLAIMS_SENT = "sent claims to the clearinghouse"
CLAIMS_NOT_SENT = "claims did not reach the clearinghouse"
CLAIMS_DOWNLOADED = "downloaded a claim file"
STORED_DOWNLOADED = "downloaded a claim file again"
USAGE_CODES = {"test": "T", "production": "P"}
MAX_CONTROL = 999_999_999
NO_CONNECTION = "set up the clearinghouse in Settings first"


@dataclass(frozen=True)
class ClaimFileOut:
    submission: ClaimSubmission
    content: bytes
    file_name: str


async def send_claims(
    db: AsyncSession, store: ObjectStore, link: FileLink, actor: Actor, note_ids: list[str] | None
) -> dict[str, Any]:
    connection = await _connection(db, actor)
    if connection.transport != "sftp" or not connection.outbound_folder:
        raise Conflict("this practice uploads claim files to its clearinghouse by hand; download the file instead")
    target = sftp_target(connection)
    built = await _build(db, store, actor, connection, await ready_claims(db, actor, note_ids))
    await db.commit()
    remote = claim_file_name(built.submission)
    try:
        await link.upload(target, connection.outbound_folder, remote, built.content)
    except (LinkRefused, Invalid) as error:
        _deliver(db, actor, built.submission, "failed", remote=remote, error=error.message[:300])
        record_access(db, actor, CLAIMS_NOT_SENT, detail=f"{_detail(built.submission)} · {error.message}"[:300])
        await db.commit()
        raise
    _deliver(db, actor, built.submission, "delivered", remote=remote)
    await mark_exported(db, built.note_ids)
    record_access(db, actor, CLAIMS_SENT, detail=_detail(built.submission))
    await db.commit()
    return {"id": built.submission.id, "claims": built.submission.claims_count, "outcome": "delivered"}


async def download_claims(
    db: AsyncSession, store: ObjectStore, actor: Actor, note_ids: list[str] | None
) -> ClaimFileOut:
    connection = await _connection(db, actor)
    built = await _build(db, store, actor, connection, await ready_claims(db, actor, note_ids))
    _deliver(db, actor, built.submission, "downloaded", remote=None)
    await mark_exported(db, built.note_ids)
    record_access(db, actor, CLAIMS_DOWNLOADED, detail=_detail(built.submission))
    await db.commit()
    return ClaimFileOut(built.submission, built.content, claim_file_name(built.submission))


async def stored_claim_file(db: AsyncSession, store: ObjectStore, actor: Actor, submission_id: str) -> ClaimFileOut:
    row = await db.get(ClaimSubmission, submission_id)
    if row is None or row.practice_id != actor.practice_id:
        raise NotFound("claim file not found")
    content = await store.get(row.file_key)
    if hashlib.sha256(content).hexdigest() != row.file_sha256:
        raise Conflict(f"the stored claim file {row.id} does not match its recorded SHA-256")
    record_access(db, actor, STORED_DOWNLOADED, detail=_detail(row))
    await db.commit()
    return ClaimFileOut(row, content, claim_file_name(row))


def claim_file_name(submission: ClaimSubmission) -> str:
    return f"bodha-837p-{submission.control_number:09d}.txt"


@dataclass(frozen=True)
class _Built:
    submission: ClaimSubmission
    content: bytes
    note_ids: list[str]


async def _connection(db: AsyncSession, actor: Actor) -> ClearinghouseConnection:
    connection = await current_connection(db, actor.practice_id)
    if connection is None:
        raise Conflict(NO_CONNECTION)
    return connection


async def _build(
    db: AsyncSession, store: ObjectStore, actor: Actor, connection: ClearinghouseConnection, ready: ReadyClaims
) -> _Built:
    claims = tuple(professional_claim(ready.context, source) for source in ready.sources)
    profile = ready.context.profile
    submission_id, control = new_id(), await _next_control(db, connection)
    claim_file = ClaimFile(
        interchange=Interchange(
            sender_qualifier=connection.sender_qualifier,
            sender_id=connection.sender_id,
            receiver_qualifier=connection.receiver_qualifier,
            receiver_id=connection.receiver_id,
            usage=USAGE_CODES[connection.usage],
            control_number=control,
            created=utcnow().astimezone(actor.zone),
            functional_id="HC",
            transaction_code="837",
            version=IMPLEMENTATION,
        ),
        batch_ref=submission_id.replace("-", "").upper(),
        submitter=Submitter(str(profile.legal_name), str(profile.contact), str(profile.phone)),
        receiver=Receiver(connection.receiver_name),
        claims=claims,
    )
    text = write_837p(claim_file)
    check_837p(text)
    content = text.encode("ascii")
    submission = await _record(db, store, actor, connection, claim_file, content=content, submission_id=submission_id)
    db.add_all(_items(submission, ready, claims))
    return _Built(submission, content, [source.note.id for source in ready.sources])


def _items(
    submission: ClaimSubmission, ready: ReadyClaims, claims: tuple[ProfessionalClaim, ...]
) -> list[ClaimSubmissionItem]:
    return [
        ClaimSubmissionItem(
            practice_id=submission.practice_id,
            submission_id=submission.id,
            note_id=source.note.id,
            approved_claim_id=source.snapshot.id,
            snapshot_revision=source.snapshot.revision,
            claim_detail_id=source.detail.id,
            payer_key=str(source.note.payer),
            claim_ref=claim.claim_ref,
            charge_cents=claim.charge_cents,
            lines_count=len(claim.lines),
        )
        for source, claim in zip(ready.sources, claims, strict=True)
        if source.snapshot is not None and source.detail is not None
    ]


async def _record(
    db: AsyncSession,
    store: ObjectStore,
    actor: Actor,
    connection: ClearinghouseConnection,
    claim_file: ClaimFile,
    *,
    content: bytes,
    submission_id: str,
) -> ClaimSubmission:
    key = claim_file_key(actor.practice_id, submission_id)
    await store.put(key, content, content_type=CLAIM_CONTENT_TYPE)
    submission = ClaimSubmission(
        id=submission_id,
        practice_id=actor.practice_id,
        connection_id=connection.id,
        delivery="sftp" if connection.transport == "sftp" else "download",
        usage=connection.usage,
        sender_qualifier=connection.sender_qualifier,
        sender_id=connection.sender_id,
        receiver_id=connection.receiver_id,
        control_number=claim_file.interchange.control_number,
        batch_ref=claim_file.batch_ref,
        file_key=key,
        file_sha256=hashlib.sha256(content).hexdigest(),
        file_bytes=len(content),
        claims_count=len(claim_file.claims),
        total_cents=sum(claim.charge_cents for claim in claim_file.claims),
        actor_id=actor.user.id,
        actor_name=actor.user.name,
        actor_role=actor.role,
        ip=actor.ip,
        user_agent=(actor.user_agent or "")[:300] or None,
    )
    db.add(submission)
    await db.flush()
    return submission


async def _next_control(db: AsyncSession, connection: ClearinghouseConnection) -> int:
    sender = f"claim-control:{connection.sender_qualifier}:{connection.sender_id}"
    await db.execute(select(func.pg_advisory_xact_lock(func.hashtextextended(sender, 0))))
    last = await db.scalar(
        select(func.max(ClaimSubmission.control_number)).where(
            ClaimSubmission.sender_qualifier == connection.sender_qualifier,
            ClaimSubmission.sender_id == connection.sender_id,
        )
    )
    control = (last or 0) + 1
    if control > MAX_CONTROL:
        raise Conflict("the interchange control numbers for this sender are used up")
    return control


def _deliver(
    db: AsyncSession, actor: Actor, submission: ClaimSubmission, outcome: str, *, remote: str | None, error: str = ""
) -> None:
    db.add(
        ClaimDelivery(
            practice_id=submission.practice_id,
            submission_id=submission.id,
            outcome=outcome,
            remote_name=remote,
            error=error or None,
            actor_id=actor.user.id,
            actor_name=actor.user.name,
        )
    )


def _detail(submission: ClaimSubmission) -> str:
    return (
        f"{submission.claims_count} claims · file {submission.control_number:09d} · {submission.usage}"
        f" · sha256 {submission.file_sha256[:12]}"
    )
