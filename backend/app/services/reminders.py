from __future__ import annotations

import logging
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.messenger import Messenger
from app.core.errors import Unavailable
from app.core.security import digest, random_token
from app.models import AddendumRequest, Note, Practice, Provider, utcnow
from app.services.addenda import send_link
from app.services.audit_log import record_activity
from app.services.placement import refresh_placement

logger = logging.getLogger("bodha.reminders")
BATCH = 100
SECOND_REMINDER_GAP = timedelta(hours=24)
LAST_REMINDER_AGE = timedelta(hours=24)
RETRY_AFTER_FAILURE = timedelta(hours=1)


async def expire_requests(db: AsyncSession) -> int:
    lapsed = (
        await db.scalars(
            select(AddendumRequest)
            .where(AddendumRequest.status == "sent", AddendumRequest.expires_at <= utcnow())
            .limit(BATCH)
            .with_for_update(skip_locked=True)
        )
    ).all()
    for request in lapsed:
        request.status, request.remind_at = "expired", None
        await db.flush()
        await refresh_placement(db, await db.get_one(Note, request.note_id))
        record_activity(db, None, "provider request expired", practice_id=request.practice_id, detail=request.note_id)
    await db.commit()
    return len(lapsed)


async def send_due_reminders(db: AsyncSession, messenger: Messenger) -> int:
    sent = 0
    for _ in range(BATCH):
        now = utcnow()
        request = await db.scalar(
            select(AddendumRequest)
            .where(
                AddendumRequest.status == "sent",
                AddendumRequest.remind_at <= now,
                AddendumRequest.expires_at > now,
            )
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        if request is None:
            break
        sent += await _remind(db, messenger, request)
    return sent


async def _remind(db: AsyncSession, messenger: Messenger, request: AddendumRequest) -> int:
    now, token = utcnow(), random_token()
    provider = await db.get_one(Provider, request.provider_id)
    practice = await db.get_one(Practice, request.practice_id)
    try:
        await send_link(messenger, provider, request.channel, token, practice, reminder=True)
    except Unavailable as error:
        logger.warning("reminder for request %s not sent: %s", request.id, error.message)
        request.remind_at = now + RETRY_AFTER_FAILURE
        await db.commit()
        return 0
    young = now - request.created_at < LAST_REMINDER_AGE
    request.token_hash, request.remind_at = digest(token), (now + SECOND_REMINDER_GAP if young else None)
    record_activity(db, None, "provider reminded", practice_id=practice.id, detail=request.note_id)
    await db.commit()
    return 1
