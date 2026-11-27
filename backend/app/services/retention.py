from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import DateTime, Integer, String, bindparam, func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.object_store import ObjectStore, access_log_archive_key, practice_prefix
from app.core.calendar import day_bounds, shift_years, zone_named
from app.core.config import get_settings
from app.core.deps import Actor
from app.core.errors import Conflict, Invalid, NotFound
from app.models import AccessLog, AddendumRequest, Analysis, Note, Practice, PracticeMembership, User, utcnow
from app.services.access_log_reports import write_csv
from app.services.audit_log import record_activity
from app.services.plan_limits import is_live, subscription_for
from app.services.user_sessions import end_practice_sessions

__all__ = [
    "CLOSABLE_STATUSES",
    "PRACTICE_CLOSED",
    "PRACTICE_PURGED",
    "AccessLogArchive",
    "close_practice",
    "purge_access_logs",
    "purge_after",
    "purge_practice",
    "retention_cutoff",
]

logger = logging.getLogger("bodha.retention")
PRACTICE_CLOSED, PRACTICE_PURGED = "practice closed", "practice purged"
CLOSABLE_STATUSES = ("ended", "blocked")
CSV_TYPE = "text/csv; charset=utf-8"
PURGE_ACCESS_LOG = text("SELECT bodha_purge_access_log(:practice, :cutoff)").bindparams(
    bindparam("practice", type_=String), bindparam("cutoff", type_=DateTime(timezone=True))
)
PURGE_AUTH_EVENTS = text("SELECT bodha_purge_auth_events(:practice, :cutoff)").bindparams(
    bindparam("practice", type_=String), bindparam("cutoff", type_=DateTime(timezone=True))
)
PURGE_PRACTICE = text("SELECT bodha_purge_practice(:practice, :days)").bindparams(
    bindparam("practice", type_=String), bindparam("days", type_=Integer)
)


@dataclass(frozen=True)
class AccessLogArchive:
    key: str
    entries: int
    sha256: str


def retention_cutoff(now: datetime, zone: ZoneInfo, years: int) -> datetime:
    if now.tzinfo is None:
        raise ValueError("now must carry a time zone")
    return day_bounds(shift_years(now.astimezone(zone).date(), -years), zone)[0]


def purge_after(closed_at: datetime) -> date:
    return (closed_at + timedelta(days=get_settings().retention_days)).date()


async def purge_access_logs(db: AsyncSession, now: datetime) -> int:
    floor = await _database_now(db) - timedelta(days=get_settings().retention_days)
    practices = (
        await db.execute(
            select(Practice.id, Practice.time_zone, Practice.access_log_years).where(Practice.status != "purged")
        )
    ).all()
    removed = 0
    for practice_id, time_zone, years in practices:
        cutoff = min(retention_cutoff(now, zone_named(time_zone), years), floor)
        removed += await db.scalar(PURGE_ACCESS_LOG, {"practice": practice_id, "cutoff": cutoff}) or 0
        await db.scalar(PURGE_AUTH_EVENTS, {"practice": practice_id, "cutoff": cutoff})
    await db.scalar(PURGE_AUTH_EVENTS, {"practice": None, "cutoff": floor})
    await db.commit()
    return removed


async def close_practice(db: AsyncSession, actor: Actor, practice_id: str, *, confirm_name: str) -> Practice:
    practice = await _confirmed_practice(db, practice_id, confirm_name, verb="close")
    if practice.status not in CLOSABLE_STATUSES:
        raise Conflict("end or block the practice before closing it")
    if is_live(await subscription_for(db, practice_id)):
        raise Conflict("cancel the practice's subscription before closing it")
    await _end_memberships(db, actor, practice.id)
    await db.execute(
        update(AddendumRequest)
        .where(AddendumRequest.practice_id == practice.id, AddendumRequest.status == "sent")
        .values(status="cancelled", remind_at=None)
    )
    queued = select(Note.id).where(Note.practice_id == practice.id)
    await db.execute(
        update(Analysis)
        .where(Analysis.status == "queued", Analysis.note_id.in_(queued))
        .values(status="superseded")
        .execution_options(synchronize_session=False)
    )
    practice.status, practice.closed_at, practice.closed_by = "closed", utcnow(), actor.user.id
    record_activity(db, actor, PRACTICE_CLOSED, practice_id=practice.id, detail=practice.name)
    await db.commit()
    return practice


async def purge_practice(
    db: AsyncSession, store: ObjectStore, actor: Actor, practice_id: str, *, confirm_name: str
) -> AccessLogArchive:
    practice = await _confirmed_practice(db, practice_id, confirm_name, verb="purge")
    if practice.status != "closed" or practice.closed_at is None:
        raise Conflict("only a closed practice can be purged")
    kept_until = practice.closed_at + timedelta(days=get_settings().retention_days)
    if await _database_now(db) < kept_until:
        raise Conflict(f"records are kept until {kept_until.date().isoformat()}; purge after that day")
    archive = await _archive_access_log(db, store, practice.id)
    days = get_settings().retention_days
    removed = await db.scalar(PURGE_PRACTICE, {"practice": practice.id, "days": days}) or 0
    detail = f"{removed} rows removed; access log export of {archive.entries} entries, sha256 {archive.sha256}"
    record_activity(db, actor, PRACTICE_PURGED, practice_id=practice.id, detail=detail)
    await db.commit()
    await _remove_practice_files(store, practice.id)
    return archive


async def _end_memberships(db: AsyncSession, actor: Actor, practice_id: str) -> None:
    members = select(User).join(PracticeMembership, PracticeMembership.user_id == User.id)
    for user in (await db.scalars(members.where(PracticeMembership.practice_id == practice_id))).all():
        await end_practice_sessions(db, user, practice_id, reason=PRACTICE_CLOSED, client=actor.client)
    await db.execute(
        update(PracticeMembership)
        .where(PracticeMembership.practice_id == practice_id, PracticeMembership.ended_at.is_(None))
        .values(ended_at=utcnow())
    )


async def _confirmed_practice(db: AsyncSession, practice_id: str, confirm_name: str, *, verb: str) -> Practice:
    practice = await db.get(Practice, practice_id, with_for_update=True, populate_existing=True)
    if practice is None:
        raise NotFound("practice not found")
    if confirm_name.strip() != practice.name:
        raise Invalid(f"type the practice name exactly as shown to {verb} it")
    return practice


async def _database_now(db: AsyncSession) -> datetime:
    return await db.scalar(select(func.clock_timestamp()))


async def _archive_access_log(db: AsyncSession, store: ObjectStore, practice_id: str) -> AccessLogArchive:
    rows = list(
        await db.scalars(select(AccessLog).where(AccessLog.practice_id == practice_id).order_by(AccessLog.chain_seq))
    )
    data = write_csv(rows).encode("utf-8")
    key = access_log_archive_key(practice_id)
    await store.put(key, data, content_type=CSV_TYPE)
    return AccessLogArchive(key, len(rows), hashlib.sha256(data).hexdigest())


async def _remove_practice_files(store: ObjectStore, practice_id: str) -> None:
    try:
        await store.delete_prefix(practice_prefix(practice_id))
    except Exception:
        logger.exception("stored files of purged practice %s were not removed", practice_id)
