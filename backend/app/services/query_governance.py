from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.messenger import Messenger
from app.core.calendar import zone_named
from app.core.config import get_settings
from app.core.deps import ACTIVE_PRACTICE_STATUSES, Actor
from app.core.errors import Conflict, NotFound, Unavailable
from app.models import AddendumRequest, Note, NoteText, Practice, Provider, User
from app.services.audit_log import record_access, record_activity
from app.services.review_actions import note_for

__all__ = [
    "ASKED_STATUSES",
    "ESCALATE_AFTER",
    "AddendumExport",
    "addendum_export",
    "escalate_unanswered",
    "escalation_text",
    "labelled_addendum",
    "refuse_repeat_queries",
    "repeat_query_blocked",
]

logger = logging.getLogger("bodha.query_governance")
ASKED_STATUSES = ("sent", "answered", "expired")
ESCALATE_AFTER = timedelta(hours=48)
ESCALATION_BATCH = 500
ESCALATED = "provider requests escalated"


@dataclass(frozen=True)
class AddendumExport:
    text: str
    file_name: str


async def repeat_query_blocked(db: AsyncSession, note: Note, question_keys: Sequence[str]) -> list[str]:
    wanted = list(dict.fromkeys(question_keys))
    if not wanted:
        return []
    earlier = (
        await db.scalars(
            select(AddendumRequest)
            .where(AddendumRequest.note_id == note.id, AddendumRequest.status.in_(ASKED_STATUSES))
            .order_by(AddendumRequest.created_at)
        )
    ).all()
    texts = (
        await db.execute(select(NoteText.created_at, NoteText.addendum_request_id).where(NoteText.note_id == note.id))
    ).all()
    blocked: set[str] = set()
    for request in earlier:
        documented = any(at > request.created_at and source != request.id for at, source in texts)
        if not documented:
            blocked |= {str(question["key"]) for question in request.questions}
    return [key for key in wanted if key in blocked]


async def refuse_repeat_queries(db: AsyncSession, note: Note, question_keys: Sequence[str]) -> None:
    repeated = await repeat_query_blocked(db, note, question_keys)
    if repeated:
        raise Conflict("already asked with no new documentation in the note since: " + ", ".join(repeated))


async def escalate_unanswered(db: AsyncSession, messenger: Messenger, now: datetime) -> int:
    if now.tzinfo is None:
        raise ValueError("now needs a time zone")
    waiting = (
        await db.scalars(
            select(AddendumRequest)
            .where(
                AddendumRequest.status == "sent",
                AddendumRequest.escalated_at.is_(None),
                AddendumRequest.created_at <= now - ESCALATE_AFTER,
                AddendumRequest.expires_at > now,
            )
            .order_by(AddendumRequest.practice_id, AddendumRequest.created_at)
            .limit(ESCALATION_BATCH)
            .with_for_update(skip_locked=True)
        )
    ).all()
    by_practice: dict[str, list[AddendumRequest]] = {}
    for request in waiting:
        by_practice.setdefault(request.practice_id, []).append(request)
    escalated = 0
    for practice_id, requests in by_practice.items():
        escalated += await _escalate_practice(db, messenger, practice_id, requests, now)
    await db.commit()
    return escalated


async def _escalate_practice(
    db: AsyncSession, messenger: Messenger, practice_id: str, requests: list[AddendumRequest], now: datetime
) -> int:
    practice = await db.get_one(Practice, practice_id)
    if practice.status not in ACTIVE_PRACTICE_STATUSES:
        return 0
    admins = (
        await db.scalars(
            select(User.email)
            .where(User.practice_id == practice_id, User.role == "admin", User.status == "active")
            .order_by(User.email)
        )
    ).all()
    subject, body = f"Provider questions waiting at {practice.name}", escalation_text(practice.name, len(requests))
    sent = 0
    for email in admins:
        try:
            await messenger.email(email, subject=subject, body=body)
            sent += 1
        except Unavailable as error:
            logger.warning("escalation for practice %s not sent to one admin: %s", practice_id, error.message)
    if sent == 0:
        return 0
    for request in requests:
        request.escalated_at = now
    record_activity(db, None, ESCALATED, practice_id=practice_id, detail=f"{len(requests)} requests, {sent} admins")
    return len(requests)


def escalation_text(practice_name: str, waiting: int) -> str:
    noun = "request has" if waiting == 1 else "requests have"
    hours = int(ESCALATE_AFTER.total_seconds() // 3600)
    return "\n".join(
        [
            f"{practice_name}: {waiting} provider question {noun} had no answer for more than {hours} hours.",
            "",
            f"Open Waiting on provider: {get_settings().app_url}/queue?lane=provider",
        ]
    )


async def addendum_export(db: AsyncSession, actor: Actor, note_id: str, *, request_id: str | None) -> AddendumExport:
    note = await note_for(db, actor, note_id)
    query = select(AddendumRequest).where(
        AddendumRequest.note_id == note.id,
        AddendumRequest.status == "answered",
        AddendumRequest.addendum_text.is_not(None),
        AddendumRequest.answered_at.is_not(None),
    )
    if request_id is not None:
        query = query.where(AddendumRequest.id == request_id)
    request = await db.scalar(query.order_by(AddendumRequest.answered_at.desc()).limit(1))
    if request is None or request.answered_at is None:
        raise NotFound("this note has no signed addendum")
    provider = await db.get_one(Provider, request.provider_id)
    practice = await db.get_one(Practice, note.practice_id)
    text = labelled_addendum(
        request.addendum_text or "",
        signed_on=request.answered_at.astimezone(zone_named(practice.time_zone)).date(),
        signed_by=f"{provider.name}, {provider.credential}",
        visit_on=note.service_date,
    )
    record_access(db, actor, "exported addendum", note_id=note.id, detail=f"request {request.id}")
    await db.commit()
    return AddendumExport(text, f"addendum-{note.id}.txt")


def labelled_addendum(text: str, *, signed_on: date, signed_by: str, visit_on: date) -> str:
    header = f"ADDENDUM — dated {_day(signed_on)} — signed by {signed_by} — refers to the visit of {_day(visit_on)}"
    return f"{header}\n\n{text.strip()}\n"


def _day(day: date) -> str:
    return day.strftime("%d %b %Y")
