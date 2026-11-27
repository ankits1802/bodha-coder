from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Actor
from app.core.errors import Conflict, Forbidden, Invalid, NotFound
from app.core.roles import ADMINS, NOTE_READERS
from app.models import Note, User
from app.services.audit_log import record_access
from app.services.memberships import ACTIVE, membership_in
from app.services.note_change_history import record_note_change
from app.services.worklists import QUEUE_STATUSES

ASSIGNED = "assigned"
NOBODY = "nobody"


async def assign_notes(db: AsyncSession, actor: Actor, note_ids: list[str], user_id: str | None) -> list[str]:
    assignee = await _assignee(db, actor, user_id)
    notes = await _open_notes(db, actor, note_ids)
    if actor.role not in ADMINS and any(note.assigned_to not in (None, actor.user.id) for note in notes):
        raise Forbidden("a note assigned to someone else can be reassigned by an admin")
    target = assignee.id if assignee else None
    for note in notes:
        if note.assigned_to == target:
            continue
        record_note_change(db, actor, note, "assignee", old=note.assigned_to, new=target)
        note.assigned_to = target
        record_access(db, actor, ASSIGNED, note_id=note.id, detail=f"to {assignee.name if assignee else NOBODY}")
    await db.commit()
    return [note.id for note in notes]


async def _assignee(db: AsyncSession, actor: Actor, user_id: str | None) -> User | None:
    if user_id is None:
        return None
    if actor.role not in ADMINS and user_id != actor.user.id:
        raise Forbidden("you can assign notes only to yourself")
    user = await db.get(User, user_id)
    membership = await membership_in(db, user_id, actor.practice_id) if user is not None else None
    if user is None or membership is None or membership.ended_at is not None:
        raise NotFound("person not found")
    if user.status != ACTIVE or membership.status != ACTIVE or membership.role not in NOTE_READERS:
        raise Invalid(f"{user.name} cannot be assigned notes")
    return user


async def _open_notes(db: AsyncSession, actor: Actor, note_ids: list[str]) -> list[Note]:
    wanted = set(note_ids)
    notes = list(
        (
            await db.scalars(
                select(Note)
                .where(Note.practice_id == actor.practice_id, Note.id.in_(wanted))
                .order_by(Note.due_at, Note.created_at)
                .with_for_update()
            )
        ).all()
    )
    if len(notes) != len(wanted):
        raise NotFound("note not found")
    if any(note.status not in QUEUE_STATUSES for note in notes):
        raise Conflict("approved and exported notes cannot be assigned")
    return notes
