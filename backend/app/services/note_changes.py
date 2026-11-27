from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Actor
from app.core.errors import Conflict, NotFound
from app.models import AddendumRequest, Note
from app.services.analysis import request_analysis
from app.services.audit_log import record_access
from app.services.note_change_history import record_note_change
from app.services.note_voids import refuse_voided
from app.services.payers import payer_list
from app.services.placement import refresh_placement
from app.services.review_actions import note_for

EDITABLE = ("queued", "ready", "failed")


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
    record_note_change(db, actor, note, "visit_type", old=previous, new=visit_type)
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
    refuse_voided(note)
    if note.status == "exported":
        raise Conflict("an exported note keeps its payer")
    known = actor.practice is not None and any(payer.get("id") == payer_id for payer in payer_list(actor.practice))
    if payer_id is not None and not known:
        raise NotFound("payer not found")
    if note.payer != payer_id:
        record_note_change(db, actor, note, "payer", old=note.payer, new=payer_id)
    note.payer = payer_id
    record_access(db, actor, "set payer", note_id=note.id)
    await db.commit()
    return note
