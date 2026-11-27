from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import delete, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.object_store import ObjectStore, note_document_revision_key, practice_prefix
from app.adapters.pdf_text import DocumentUnreadable, read_pdf_text
from app.core.calendar import day_bounds, shift_years, zone_named
from app.core.deps import Actor
from app.core.errors import Conflict, Invalid, NotFound
from app.models import (
    DEFAULT_TIME_ZONE,
    AccessLog,
    Activity,
    AddendumRequest,
    Analysis,
    ApprovedClaim,
    AuditPackage,
    AuditSample,
    AuthEvent,
    Batch,
    ClaimExport,
    ClaimExportItem,
    CodeSet,
    Decision,
    EvalCase,
    EvalRun,
    MipsList,
    Note,
    NoteText,
    Practice,
    PracticeMembership,
    Provider,
    ProviderAttestation,
    RecoveryCode,
    Remittance,
    RemittanceLine,
    ReviewComment,
    ReviewCommentRemoval,
    Session,
    Subscription,
    Suggestion,
    User,
    UserIdentity,
    UserToken,
)
from app.services.analysis import next_revision, request_analysis
from app.services.audit_log import record_access, record_activity
from app.services.plan_limits import is_live, subscription_for
from app.services.practice_setup import ACCESS_LOG_YEARS
from app.services.uploads import check_pdf
from app.services.worklists import count_of

__all__ = [
    "ACCESS_LOG_PAGE",
    "PRACTICE_DELETED",
    "NewDocument",
    "access_log_page",
    "delete_practice",
    "purge_access_logs",
    "replace_document",
    "retention_cutoff",
]

logger = logging.getLogger("bodha.records")
ACCESS_LOG_PAGE = 200
PRACTICE_DELETED = "practice deleted"
FIXED_DOCUMENT_STATUSES = ("exported", "reading")
DELETABLE_PRACTICE_STATUSES = ("ended", "blocked")
MIN_RETENTION_YEARS = min(ACCESS_LOG_YEARS)
NOTE_CHILDREN = (Decision, Suggestion, NoteText)
REVIEW_RECORD_TABLES = (
    ReviewCommentRemoval,
    ReviewComment,
    ProviderAttestation,
    AuditPackage,
    ClaimExportItem,
    ClaimExport,
)
QUALITY_AND_REMITTANCE_TABLES = (AuditSample, EvalCase, EvalRun, Remittance)
PRACTICE_TABLES = (Note, Batch, Provider, MipsList, AccessLog, Activity, Subscription)
USER_CHILDREN = (UserToken, Session, RecoveryCode, UserIdentity)


@dataclass(frozen=True)
class NewDocument:
    name: str
    data: bytes


async def replace_document(
    db: AsyncSession, store: ObjectStore, actor: Actor, note_id: str, document: NewDocument
) -> Note:
    note = await _locked_note(db, actor, note_id)
    await _check_replaceable(db, note)
    check_pdf(document.name, document.data)
    text = _document_text(document)
    sha256 = hashlib.sha256(document.data).hexdigest()
    await _check_new_file(db, note, sha256)
    revision = await next_revision(db, NoteText, note.id)
    key = note_document_revision_key(note.practice_id, note.id, revision)
    await store.put(key, document.data, content_type="application/pdf")
    db.add(NoteText(note_id=note.id, revision=revision, source="document", text=text))
    note.file_key, note.file_name, note.file_sha256 = key, document.name[:255], sha256
    note.file_bytes, note.status, note.approved_by, note.approved_at = len(document.data), "queued", None, None
    await db.execute(
        update(Analysis).where(Analysis.note_id == note.id, Analysis.status == "queued").values(status="superseded")
    )
    await request_analysis(db, note, reason="document")
    record_access(db, actor, "replaced PDF", note_id=note.id, detail=f"document revision {revision}")
    await db.commit()
    return note


async def _locked_note(db: AsyncSession, actor: Actor, note_id: str) -> Note:
    note = await db.scalar(
        select(Note).where(Note.id == note_id, Note.practice_id == actor.practice_id).with_for_update()
    )
    if note is None:
        raise NotFound("note not found")
    return note


async def _check_replaceable(db: AsyncSession, note: Note) -> None:
    if note.status in FIXED_DOCUMENT_STATUSES:
        raise Conflict("the PDF of an exported note or a note being read cannot be replaced")
    open_request = await db.scalar(
        select(AddendumRequest.id).where(AddendumRequest.note_id == note.id, AddendumRequest.status == "sent")
    )
    if open_request is not None:
        raise Conflict("cancel the open provider request before replacing the PDF")


def _document_text(document: NewDocument) -> str:
    try:
        read = read_pdf_text(document.data)
    except DocumentUnreadable as error:
        raise Invalid(f"{document.name}: {error}") from error
    return read.text if read.has_text_layer else ""


async def _check_new_file(db: AsyncSession, note: Note, sha256: str) -> None:
    holder = await db.scalar(select(Note.id).where(Note.practice_id == note.practice_id, Note.file_sha256 == sha256))
    if holder == note.id:
        raise Conflict("this PDF is already the note's document")
    if holder is not None:
        raise Conflict("this PDF is already uploaded as another note")


async def access_log_page(
    db: AsyncSession, actor: Actor, *, day: date, user_id: str | None, offset: int
) -> dict[str, Any]:
    start, end = day_bounds(day, actor.zone)
    query = select(AccessLog).where(
        AccessLog.practice_id == actor.practice_id, AccessLog.created_at >= start, AccessLog.created_at < end
    )
    if user_id:
        query = query.where(AccessLog.actor_id == user_id)
    rows = await db.scalars(
        query.order_by(AccessLog.created_at.desc(), AccessLog.id).offset(offset).limit(ACCESS_LOG_PAGE)
    )
    return {
        "items": [_access_entry(row) for row in rows],
        "total": await count_of(db, query),
        "offset": offset,
        "page_size": ACCESS_LOG_PAGE,
    }


def _access_entry(row: AccessLog) -> dict[str, Any]:
    return {
        "at": row.created_at.isoformat(),
        "actor": row.actor_name,
        "actor_kind": row.actor_kind,
        "action": row.action,
        "note_id": row.note_id,
        "detail": row.detail,
        "ip": row.ip,
        "user_agent": row.user_agent,
    }


def retention_cutoff(now: datetime, zone: ZoneInfo, years: int) -> datetime:
    if now.tzinfo is None:
        raise ValueError("now must carry a time zone")
    return day_bounds(shift_years(now.astimezone(zone).date(), -years), zone)[0]


async def purge_access_logs(db: AsyncSession, now: datetime) -> int:
    practices = (await db.execute(select(Practice.id, Practice.time_zone, Practice.access_log_years))).all()
    removed = 0
    for practice_id, time_zone, years in practices:
        cutoff = retention_cutoff(now, zone_named(time_zone), years)
        result = await db.execute(
            delete(AccessLog).where(AccessLog.practice_id == practice_id, AccessLog.created_at < cutoff)
        )
        removed += result.rowcount or 0
        await db.execute(delete(AuthEvent).where(AuthEvent.practice_id == practice_id, AuthEvent.created_at < cutoff))
    await db.execute(delete(AuthEvent).where(AuthEvent.practice_id.is_(None), AuthEvent.created_at < _oldest_kept(now)))
    await db.commit()
    return removed


def _oldest_kept(now: datetime) -> datetime:
    return retention_cutoff(now, zone_named(DEFAULT_TIME_ZONE), MIN_RETENTION_YEARS)


async def delete_practice(
    db: AsyncSession, store: ObjectStore, actor: Actor, practice_id: str, *, confirm_name: str
) -> None:
    practice = await db.get(Practice, practice_id, with_for_update=True)
    if practice is None:
        raise NotFound("practice not found")
    if practice.status not in DELETABLE_PRACTICE_STATUSES:
        raise Conflict("end or block the practice before deleting it")
    if confirm_name.strip() != practice.name:
        raise Invalid("type the practice name exactly as shown to delete it")
    if is_live(await subscription_for(db, practice_id)):
        raise Conflict("cancel the practice's subscription before deleting it")
    name = practice.name
    await _delete_practice_rows(db, practice_id)
    record_activity(db, actor, PRACTICE_DELETED, practice_id=practice_id, detail=name)
    await db.commit()
    await _remove_practice_files(store, practice_id)


async def _delete_practice_rows(db: AsyncSession, practice_id: str) -> None:
    notes = select(Note.id).where(Note.practice_id == practice_id)
    users = await _people_only_here(db, practice_id)
    remittances = select(Remittance.id).where(Remittance.practice_id == practice_id)
    await db.execute(delete(RemittanceLine).where(RemittanceLine.remittance_id.in_(remittances)))
    for table in QUALITY_AND_REMITTANCE_TABLES:
        await db.execute(delete(table).where(table.practice_id == practice_id))
    for table in REVIEW_RECORD_TABLES:
        await db.execute(delete(table).where(table.practice_id == practice_id))
    for table in NOTE_CHILDREN:
        await db.execute(delete(table).where(table.note_id.in_(notes)))
    await db.execute(delete(AddendumRequest).where(AddendumRequest.practice_id == practice_id))
    await db.execute(delete(ApprovedClaim).where(ApprovedClaim.practice_id == practice_id))
    for table in (Analysis, CodeSet):
        await db.execute(delete(table).where(table.note_id.in_(notes)))
    for table in PRACTICE_TABLES:
        await db.execute(delete(table).where(table.practice_id == practice_id))
    await _forget_practice_people(db, practice_id, users)
    await db.execute(delete(Practice).where(Practice.id == practice_id))


async def _people_only_here(db: AsyncSession, practice_id: str) -> list[str]:
    elsewhere = select(PracticeMembership.user_id).where(PracticeMembership.practice_id != practice_id)
    members = select(PracticeMembership.user_id).where(
        PracticeMembership.practice_id == practice_id, PracticeMembership.user_id.not_in(elsewhere)
    )
    return list((await db.scalars(members)).all())


async def _forget_practice_people(db: AsyncSession, practice_id: str, users: list[str]) -> None:
    await db.execute(delete(Session).where(Session.practice_id == practice_id))
    await db.execute(delete(AuthEvent).where(or_(AuthEvent.practice_id == practice_id, AuthEvent.user_id.in_(users))))
    await db.execute(delete(PracticeMembership).where(PracticeMembership.practice_id == practice_id))
    for table in USER_CHILDREN:
        await db.execute(delete(table).where(table.user_id.in_(users)))
    await db.execute(delete(User).where(User.id.in_(users)))
    await db.execute(update(User).where(User.last_practice_id == practice_id).values(last_practice_id=None))
    await db.execute(update(User).where(User.legacy_practice_id == practice_id).values(legacy_practice_id=None))


async def _remove_practice_files(store: ObjectStore, practice_id: str) -> None:
    try:
        await store.delete_prefix(practice_prefix(practice_id))
    except Exception:
        logger.exception("stored files of deleted practice %s were not removed", practice_id)
