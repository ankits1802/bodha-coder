from __future__ import annotations

import logging
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.object_store import ObjectStore
from app.adapters.sftp import FileLink, RemoteFile
from app.core.config import get_settings
from app.core.db import exclusive_job
from app.core.deps import ACTIVE_PRACTICE_STATUSES
from app.core.errors import AppError
from app.core.security import digest
from app.models import ClaimAckFile, ClearinghouseConnection, Practice
from app.services.claim_acks import AckOrigin, ingest_ack_file
from app.services.clearinghouse_settings import sftp_target

__all__ = ["CLOCK_SKEW", "MAX_FILES_PER_POLL", "poll_acknowledgments"]

logger = logging.getLogger("bodha.clearinghouse")
POLL_LOCK = "clearinghouse acknowledgments"
MAX_FILES_PER_POLL = 50
CLOCK_SKEW = timedelta(days=1)


async def poll_acknowledgments(db: AsyncSession, store: ObjectStore, link: FileLink, now: datetime) -> int:
    if now.tzinfo is None:
        raise ValueError("now needs a time zone")
    async with exclusive_job(db, POLL_LOCK) as held:
        if not held:
            return 0
        connection_ids = list(
            await db.scalars(
                select(ClearinghouseConnection.id)
                .join(Practice, Practice.id == ClearinghouseConnection.practice_id)
                .where(
                    ClearinghouseConnection.retired_at.is_(None),
                    ClearinghouseConnection.transport == "sftp",
                    Practice.status.in_(ACTIVE_PRACTICE_STATUSES),
                )
            )
        )
        fetched = 0
        for connection_id in connection_ids:
            fetched += await _poll_safely(db, store, link, connection_id)
        return fetched


async def _poll_safely(db: AsyncSession, store: ObjectStore, link: FileLink, connection_id: str) -> int:
    connection = await db.get_one(ClearinghouseConnection, connection_id)
    practice_id = connection.practice_id
    try:
        fetched = await _poll(db, store, link, connection)
    except AppError as error:
        await db.rollback()
        logger.warning("clearinghouse poll failed", extra={"fields": {"practice": practice_id, "reason": error.code}})
        return 0
    if fetched:
        logger.info("clearinghouse responses fetched", extra={"fields": {"practice": practice_id, "files": fetched}})
    return fetched


async def _poll(db: AsyncSession, store: ObjectStore, link: FileLink, connection: ClearinghouseConnection) -> int:
    target, folder = sftp_target(connection), str(connection.inbound_folder)
    listed = [
        item for item in await link.listing(target, folder) if item.modified >= connection.created_at - CLOCK_SKEW
    ]
    fresh = await _unseen(db, connection.practice_id, listed)
    if not fresh:
        return 0
    limit = get_settings().max_upload_mb * 1024 * 1024
    downloaded = await link.download(target, folder, [item.name for item in fresh], limit=limit)
    for name, data in downloaded:
        origin = AckOrigin(connection.practice_id, "sftp", connection_id=connection.id, remote_name=name)
        await ingest_ack_file(db, store, origin, data)
        await db.commit()
    return len(downloaded)


async def _unseen(db: AsyncSession, practice_id: str, listed: list[RemoteFile]) -> list[RemoteFile]:
    by_digest = {digest(item.name): item for item in listed}
    if not by_digest:
        return []
    seen = set(
        await db.scalars(
            select(ClaimAckFile.remote_name_sha256).where(
                ClaimAckFile.practice_id == practice_id, ClaimAckFile.remote_name_sha256.in_(by_digest)
            )
        )
    )
    fresh = [item for key, item in by_digest.items() if key not in seen]
    return sorted(fresh, key=lambda item: item.modified)[:MAX_FILES_PER_POLL]
