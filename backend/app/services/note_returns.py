from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Actor
from app.core.errors import Invalid
from app.models import OVERRIDE_NOTE_LENGTH, RETURN_REASONS, Decision, Note, NoteReturn, User
from app.services.audit_log import record_access
from app.services.finding import Finding
from app.services.inbox import Notice, notify
from app.services.note_change_history import record_note_change
from app.services.placement import current_findings, refresh_placement
from app.services.review_actions import allowed_choices
from app.services.routing import CHANGE_KINDS

__all__ = [
    "OTHER_RETURN_REASON",
    "RETURNED_TO_CODER",
    "RETURN_REASON_LABELS",
    "ReturnReason",
    "checked_return_reason",
    "open_return",
    "return_records",
    "return_recipient",
    "return_text",
    "return_to_coder",
    "returned_items",
    "undecided_items",
]

OTHER_RETURN_REASON = "other"
RETURNED_TO_CODER = "returned to coder"
RISK_PREFIX = "hcc"
DETAIL_LENGTH = 300
RETURN_REASON_LABELS = {
    "level_not_supported": "Level not supported",
    "documentation_missing": "Documentation missing",
    "coding_error": "Coding error",
    "ask_provider": "Ask the provider",
    "payer_policy": "Payer policy",
    "other": "Other",
}


@dataclass(frozen=True)
class ReturnReason:
    reason: str
    note: str | None


def checked_return_reason(reason: str, note: str | None) -> ReturnReason:
    if reason not in RETURN_REASONS:
        raise Invalid(f"{reason} is not a return reason")
    text = (note or "").strip()
    if len(text) > OVERRIDE_NOTE_LENGTH:
        raise Invalid(f"a return note is at most {OVERRIDE_NOTE_LENGTH} characters")
    if reason == OTHER_RETURN_REASON and not text:
        raise Invalid("write a short note when the reason is Other")
    return ReturnReason(reason, text or None)


def return_text(reason: str, note: str | None) -> str:
    label = RETURN_REASON_LABELS.get(reason, reason)
    return f"{label}: {note}" if note else label


def returned_items(findings: Iterable[Finding]) -> list[str]:
    return [
        finding.key
        for finding in findings
        if finding.kind in CHANGE_KINDS
        and not finding.key.startswith(RISK_PREFIX)
        and len(allowed_choices(finding)) >= 2
    ]


async def return_to_coder(db: AsyncSession, actor: Actor, note: Note, reason: ReturnReason) -> NoteReturn:
    said = return_text(reason.reason, reason.note)
    record = NoteReturn(
        practice_id=note.practice_id,
        note_id=note.id,
        analysis_id=note.current_analysis_id,
        actor_id=actor.user.id,
        actor_role=actor.role,
        reason=reason.reason,
        note=reason.note,
        flag_reason=note.flag_reason,
        finding_keys=returned_items(await current_findings(db, note)),
    )
    db.add(record)
    record_note_change(db, actor, note, "flag", old=note.flag_reason, new=None, reason=said)
    await db.flush()
    recipient = await return_recipient(db, note, actor)
    note.flag_reason, note.compliance_cleared_by, note.returned_at = None, actor.user.id, record.created_at
    await refresh_placement(db, note)
    record_access(db, actor, RETURNED_TO_CODER, note_id=note.id, detail=said[:DETAIL_LENGTH])
    if recipient is not None:
        notice = Notice(
            kind="compliance_returned",
            actor_name=actor.user.name,
            actor_id=actor.user.id,
            note_id=note.id,
            payload={"reason": reason.reason},
        )
        await notify(db, note.practice_id, [recipient], notice)
    return record


async def return_recipient(db: AsyncSession, note: Note, actor: Actor) -> str | None:
    for candidate in (note.flagged_by, note.assigned_to):
        if candidate and candidate != actor.user.id:
            return candidate
    return await db.scalar(
        select(Decision.actor_id)
        .where(Decision.note_id == note.id, Decision.actor_id != actor.user.id)
        .order_by(Decision.created_at.desc())
        .limit(1)
    )


async def open_return(db: AsyncSession, note: Note) -> NoteReturn | None:
    if note.returned_at is None:
        return None
    return await db.scalar(
        select(NoteReturn).where(NoteReturn.note_id == note.id).order_by(NoteReturn.created_at.desc()).limit(1)
    )


async def undecided_items(db: AsyncSession, note: Note, findings: Iterable[Finding]) -> list[str]:
    opened = await open_return(db, note)
    if opened is None or note.returned_at is None:
        return []
    present = {finding.key for finding in findings}
    decided = set(
        await db.scalars(
            select(Decision.suggestion_key).where(Decision.note_id == note.id, Decision.created_at > note.returned_at)
        )
    )
    return [key for key in opened.finding_keys if key in present and key not in decided]


async def return_records(db: AsyncSession, note_id: str) -> list[dict[str, Any]]:
    rows = await db.execute(
        select(NoteReturn, User.name)
        .outerjoin(User, User.id == NoteReturn.actor_id)
        .where(NoteReturn.note_id == note_id)
        .order_by(NoteReturn.created_at, NoteReturn.id)
    )
    return [
        {
            "reason": row.reason,
            "note": row.note,
            "by": name,
            "role": row.actor_role,
            "at": row.created_at.isoformat(),
            "flag_reason": row.flag_reason,
        }
        for row, name in rows.tuples()
    ]
