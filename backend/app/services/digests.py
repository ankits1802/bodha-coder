from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, time

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.messenger import Messenger
from app.core.calendar import zone_named
from app.core.config import get_settings
from app.core.deps import ACTIVE_PRACTICE_STATUSES, Actor
from app.core.errors import Unavailable
from app.core.roles import NOTE_READERS
from app.models import LANES, Activity, Note, Practice, User
from app.services.audit_log import record_activity
from app.services.worklists import QUEUE_STATUSES, lane_counts

logger = logging.getLogger("bodha.digests")
DIGEST_TIME = time(7)
DIGEST_SENT = "digest sent"
PREFERENCE_CHANGED = "digest preference"
LANE_NAMES = {
    "approve": "Ready to approve",
    "coder": "Needs a coder",
    "provider": "Waiting on provider",
    "compliance": "Compliance",
}


@dataclass(frozen=True)
class DigestPractice:
    id: str
    name: str
    day: date


@dataclass(frozen=True)
class Recipient:
    id: str
    email: str


async def send_due_digests(db: AsyncSession, messenger: Messenger, now: datetime) -> int:
    if now.tzinfo is None:
        raise ValueError("now needs a time zone")
    sent = 0
    for practice in await _due_practices(db, now):
        if await _claim(db, practice):
            sent += await _send_practice_digest(db, messenger, practice, now)
    await db.commit()
    return sent


def digest_text(practice: DigestPractice, lanes: dict[str, dict[str, int]], assigned: int) -> str:
    waiting = sum(item["total"] for item in lanes.values())
    due_soon = sum(item["due_soon"] for item in lanes.values())
    lines = [
        f"{practice.name}, {practice.day.strftime('%A %d %B %Y')}",
        "",
        f"Waiting for review: {waiting}",
        *(f"{LANE_NAMES[lane]}: {lanes[lane]['total']}" for lane in LANES),
        f"Due within 24 hours: {due_soon}",
        f"Assigned to you: {assigned}",
        "",
        f"Open Today: {get_settings().app_url}/today",
    ]
    return "\n".join(lines)


async def set_digest_preference(db: AsyncSession, actor: Actor, *, enabled: bool) -> bool:
    actor.user.notify_digest = enabled
    record_activity(db, actor, PREFERENCE_CHANGED, practice_id=actor.practice_id, detail="on" if enabled else "off")
    await db.commit()
    return actor.user.notify_digest


async def _due_practices(db: AsyncSession, now: datetime) -> list[DigestPractice]:
    rows = await db.execute(
        select(Practice.id, Practice.name, Practice.time_zone, Practice.renews_on)
        .where(Practice.status.in_(ACTIVE_PRACTICE_STATUSES))
        .order_by(Practice.created_at)
    )
    due: list[DigestPractice] = []
    for practice_id, name, zone, renews_on in rows.all():
        local = now.astimezone(zone_named(zone))
        if local.time() >= DIGEST_TIME and (renews_on is None or renews_on >= local.date()):
            due.append(DigestPractice(practice_id, name, local.date()))
    return due


async def _claim(db: AsyncSession, practice: DigestPractice) -> bool:
    lock = func.pg_try_advisory_xact_lock(func.hashtextextended(f"digest:{practice.id}", 0))
    if not await db.scalar(select(lock)):
        return False
    sent_before = await db.scalar(
        select(Activity.id)
        .where(
            Activity.practice_id == practice.id,
            Activity.action == DIGEST_SENT,
            Activity.detail == practice.day.isoformat(),
        )
        .limit(1)
    )
    return sent_before is None


async def _send_practice_digest(db: AsyncSession, messenger: Messenger, practice: DigestPractice, now: datetime) -> int:
    lanes = await lane_counts(db, practice.id, now=now)
    assigned = await _assigned_counts(db, practice.id)
    subject = f"Daily summary for {practice.name}"
    sent = 0
    for person in await _recipients(db, practice.id):
        sent += await _send(messenger, person, subject, digest_text(practice, lanes, assigned.get(person.id, 0)))
    record_activity(db, None, DIGEST_SENT, practice_id=practice.id, detail=practice.day.isoformat())
    await db.commit()
    return sent


async def _assigned_counts(db: AsyncSession, practice_id: str) -> dict[str, int]:
    rows = await db.execute(
        select(Note.assigned_to, func.count())
        .where(
            Note.practice_id == practice_id,
            Note.status.in_(QUEUE_STATUSES),
            Note.assigned_to.is_not(None),
        )
        .group_by(Note.assigned_to)
    )
    return {user_id: count for user_id, count in rows.all()}


async def _recipients(db: AsyncSession, practice_id: str) -> list[Recipient]:
    rows = await db.execute(
        select(User.id, User.email)
        .where(
            User.practice_id == practice_id,
            User.status == "active",
            User.notify_digest.is_(True),
            User.role.in_(NOTE_READERS),
        )
        .order_by(User.email)
    )
    return [Recipient(user_id, email) for user_id, email in rows.all()]


async def _send(messenger: Messenger, person: Recipient, subject: str, body: str) -> int:
    try:
        await messenger.email(person.email, subject=subject, body=body)
    except Unavailable as error:
        logger.warning("daily summary for user %s not sent: %s", person.id, error.message)
        return 0
    return 1
