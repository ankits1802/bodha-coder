from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Actor
from app.core.errors import Conflict, Forbidden, Invalid, NotFound
from app.core.roles import ADMINS
from app.models import VOIDED, AddendumRequest, Analysis, Note, utcnow
from app.services.analysis import request_analysis
from app.services.audit_log import record_access
from app.services.note_history import record_note_change

__all__ = [
    "REASON_LENGTH",
    "VOIDABLE_UNREAD",
    "VOIDED_NOTE",
    "refuse_voided",
    "restore_note",
    "void_notes",
]

REASON_LENGTH = 2000
VOIDABLE_UNREAD = ("queued", "failed")
IN_FLIGHT = ("reading", VOIDED)
VOIDED_NOTE = "this note is voided; an admin can restore it"
VOIDED_ACTION, RESTORED_ACTION = "voided note", "restored note"


def refuse_voided(note: Note) -> None:
    if note.status == VOIDED:
        raise Conflict(VOIDED_NOTE)


async def void_notes(db: AsyncSession, actor: Actor, note_ids: list[str], reason: str) -> list[str]:
    why = _reason(reason)
    notes = await _locked_notes(db, actor, note_ids)
    for note in notes:
        await _check_voidable(db, actor, note)
    for note in notes:
        await _void(db, actor, note, why)
    await db.commit()
    return [note.id for note in notes]


async def restore_note(db: AsyncSession, actor: Actor, note_id: str, reason: str) -> Note:
    why = _reason(reason)
    note = (await _locked_notes(db, actor, [note_id]))[0]
    if note.status != VOIDED:
        raise Conflict("only a voided note can be restored")
    await _refuse_taken_file(db, note)
    restored = note.status_before_void or "failed"
    note.status, note.status_before_void = restored, None
    note.voided_at, note.voided_by, note.void_reason = None, None, None
    if restored == "queued":
        await request_analysis(db, note, reason="restored")
    record_note_change(db, actor, note, "status", old=VOIDED, new=restored, reason=why)
    record_access(db, actor, RESTORED_ACTION, note_id=note.id, detail=f"back to {restored}")
    try:
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise Conflict("another note now holds this PDF") from error
    return note


def _reason(reason: str) -> str:
    why = reason.strip()
    if not why:
        raise Invalid("give the reason")
    if len(why) > REASON_LENGTH:
        raise Invalid(f"keep the reason under {REASON_LENGTH} characters")
    return why


async def _locked_notes(db: AsyncSession, actor: Actor, note_ids: list[str]) -> list[Note]:
    wanted = set(note_ids)
    query = select(Note).where(Note.practice_id == actor.practice_id, Note.id.in_(wanted)).with_for_update()
    notes = list((await db.scalars(query.order_by(Note.id))).all())
    if not wanted or len(notes) != len(wanted):
        raise NotFound("note not found")
    return notes


async def _check_voidable(db: AsyncSession, actor: Actor, note: Note) -> None:
    if note.status in IN_FLIGHT:
        raise Conflict("a note being read or already voided cannot be voided")
    unread = note.status in VOIDABLE_UNREAD and note.current_analysis_id is None
    if actor.user.role not in ADMINS and not unread:
        raise Forbidden("only an admin can void a note Bodha has read")
    open_request = await db.scalar(
        select(AddendumRequest.id).where(AddendumRequest.note_id == note.id, AddendumRequest.status == "sent")
    )
    if open_request is not None:
        raise Conflict("cancel the open provider request before voiding")


async def _void(db: AsyncSession, actor: Actor, note: Note, why: str) -> None:
    previous = note.status
    await db.execute(
        update(Analysis).where(Analysis.note_id == note.id, Analysis.status == "queued").values(status="superseded")
    )
    note.status, note.status_before_void = VOIDED, previous
    note.voided_at, note.voided_by, note.void_reason = utcnow(), actor.user.id, why
    record_note_change(db, actor, note, "status", old=previous, new=VOIDED, reason=why)
    record_access(db, actor, VOIDED_ACTION, note_id=note.id, detail=f"was {previous}")


async def _refuse_taken_file(db: AsyncSession, note: Note) -> None:
    holder = await db.scalar(
        select(Note.id).where(
            Note.practice_id == note.practice_id,
            Note.file_sha256 == note.file_sha256,
            Note.status != VOIDED,
            Note.id != note.id,
        )
    )
    if holder is not None:
        raise Conflict("another note now holds this PDF")
