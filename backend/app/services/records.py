from __future__ import annotations

import hashlib
from dataclasses import dataclass

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.object_store import ObjectStore, note_document_revision_key
from app.adapters.pdf_text import DocumentUnreadable, read_pdf_text
from app.core.deps import Actor
from app.core.errors import Conflict, Invalid, NotFound
from app.models import VOIDED, AddendumRequest, Analysis, Note, NoteText
from app.services.analysis import next_revision, request_analysis
from app.services.audit_log import record_access
from app.services.uploads import check_pdf

__all__ = ["NewDocument", "replace_document"]

FIXED_DOCUMENT_STATUSES = ("exported", "reading", VOIDED)


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
        raise Conflict("the PDF of an exported, voided or being-read note cannot be replaced")
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
    holder = await db.scalar(
        select(Note.id).where(Note.practice_id == note.practice_id, Note.file_sha256 == sha256, Note.status != VOIDED)
    )
    if holder == note.id:
        raise Conflict("this PDF is already the note's document")
    if holder is not None:
        raise Conflict("this PDF is already uploaded as another note")
