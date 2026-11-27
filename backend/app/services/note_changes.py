from __future__ import annotations

import logging

from sqlalchemy import delete, exists, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.object_store import ObjectStore, note_prefix
from app.core.deps import Actor
from app.core.errors import Conflict, NotFound
from app.models import (
    AddendumRequest,
    Analysis,
    AuditSample,
    Batch,
    CodeSet,
    Decision,
    EvalCase,
    Note,
    NoteText,
    RemittanceLine,
    Suggestion,
)
from app.services.analysis import request_analysis
from app.services.audit_log import record_access
from app.services.payers import payer_list
from app.services.placement import refresh_placement
from app.services.review_actions import note_for

logger = logging.getLogger("bodha.notes")
DELETABLE = ("queued", "ready", "failed", "approved")
EDITABLE = ("queued", "ready", "failed")
CHILD_TABLES = (Decision, Suggestion, AuditSample, EvalCase, NoteText, AddendumRequest, Analysis, CodeSet)


async def delete_notes(db: AsyncSession, store: ObjectStore, actor: Actor, note_ids: list[str]) -> list[str]:
    wanted = set(note_ids)
    notes = list(
        (
            await db.scalars(
                select(Note).where(Note.practice_id == actor.practice_id, Note.id.in_(wanted)).with_for_update()
            )
        ).all()
    )
    if len(notes) != len(wanted):
        raise NotFound("note not found")
    if any(note.status not in DELETABLE for note in notes):
        raise Conflict("exported notes and notes being read cannot be deleted")
    ids = [note.id for note in notes]
    folders = [note_prefix(note.practice_id, note.id) for note in notes]
    await db.execute(update(RemittanceLine).where(RemittanceLine.note_id.in_(ids)).values(note_id=None))
    for table in CHILD_TABLES:
        await db.execute(delete(table).where(table.note_id.in_(ids)))
    await db.execute(delete(Note).where(Note.id.in_(ids)))
    batch_ids = {note.batch_id for note in notes}
    await db.execute(delete(Batch).where(Batch.id.in_(batch_ids), ~exists().where(Note.batch_id == Batch.id)))
    for note in notes:
        record_access(db, actor, "deleted note", note_id=note.id, detail=note.file_name)
    await db.commit()
    await _remove_files(store, folders)
    return ids


async def _remove_files(store: ObjectStore, folders: list[str]) -> None:
    try:
        for folder in folders:
            await store.delete_prefix(folder)
    except Exception:
        logger.exception("stored files of deleted notes were not removed")


async def change_visit_type(db: AsyncSession, actor: Actor, note_id: str, visit_type: str) -> Note:
    note = await note_for(db, actor, note_id)
    if note.status not in EDITABLE:
        raise Conflict("reopen the note before changing its visit type")
    if note.visit_type == visit_type:
        return note
    previous, note.visit_type = note.visit_type, visit_type
    if note.status != "queued":
        note.status = "queued"
        await request_analysis(db, note, reason="visit_type")
    record_access(db, actor, "changed visit type", note_id=note.id, detail=f"{previous} to {visit_type}")
    await db.commit()
    return note


async def cancel_request(db: AsyncSession, actor: Actor, note_id: str) -> Note:
    note = await note_for(db, actor, note_id)
    request = await db.scalar(
        select(AddendumRequest).where(AddendumRequest.note_id == note.id, AddendumRequest.status == "sent")
    )
    if request is None:
        raise NotFound("no open request for this note")
    request.status, request.remind_at = "cancelled", None
    await db.flush()
    await refresh_placement(db, note)
    record_access(db, actor, "cancelled provider request", note_id=note.id)
    await db.commit()
    return note


async def set_payer(db: AsyncSession, actor: Actor, note_id: str, payer_id: str | None) -> Note:
    note = await note_for(db, actor, note_id)
    if note.status == "exported":
        raise Conflict("an exported note keeps its payer")
    known = actor.practice is not None and any(payer.get("id") == payer_id for payer in payer_list(actor.practice))
    if payer_id is not None and not known:
        raise NotFound("payer not found")
    note.payer = payer_id
    record_access(db, actor, "set payer", note_id=note.id)
    await db.commit()
    return note
