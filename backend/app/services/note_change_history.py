from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Actor
from app.models import Note, NoteChange, Practice
from app.services.memberships import member_names
from app.services.payers import payer_list

__all__ = ["LABELLED_FIELDS", "note_change_rows", "record_note_change"]

LABELLED_FIELDS = ("assignee", "payer")


def record_note_change(
    db: AsyncSession,
    actor: Actor,
    note: Note,
    field: str,
    *,
    old: str | None,
    new: str | None,
    reason: str | None = None,
) -> None:
    db.add(
        NoteChange(note_id=note.id, actor_id=actor.user.id, field=field, old_value=old, new_value=new, reason=reason)
    )


async def note_change_rows(db: AsyncSession, note_id: str, practice_id: str) -> list[dict[str, Any]]:
    labels = await _labels(db, practice_id)
    rows = await db.scalars(
        select(NoteChange).where(NoteChange.note_id == note_id).order_by(NoteChange.created_at, NoteChange.id)
    )
    return [
        {
            "field": row.field,
            "old": _shown(row.field, row.old_value, labels),
            "new": _shown(row.field, row.new_value, labels),
            "reason": row.reason,
            "by": labels.get(row.actor_id or ""),
            "at": row.created_at.isoformat(),
        }
        for row in rows
    ]


async def _labels(db: AsyncSession, practice_id: str) -> dict[str, str]:
    practice = await db.get_one(Practice, practice_id)
    payers = {payer["id"]: payer["name"] for payer in payer_list(practice) if payer.get("id")}
    return {**payers, **await member_names(db, practice_id)}


def _shown(field: str, value: str | None, labels: Mapping[str, str]) -> str | None:
    if value is None or field not in LABELLED_FIELDS:
        return value
    return labels.get(value, value)
