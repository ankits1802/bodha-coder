from __future__ import annotations

import hashlib
import logging
import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import PurePosixPath

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.adapters.object_listing import ListingStore
from app.core.calendar import zone_named
from app.core.deps import ACTIVE_PRACTICE_STATUSES, Actor
from app.core.errors import AppError, Invalid
from app.models import Practice, User
from app.services.audit_log import record_activity
from app.services.intake_settings import PROCESSED, REJECTED, IntakeConfig, inbox_prefix, intake_config
from app.services.uploads import UploadFile, UploadPlan, billed_codes_for, check_pdf, create_upload

__all__ = ["INTAKE_AGENT", "InboxGroup", "InboxSort", "poll_intake", "sort_inbox"]

logger = logging.getLogger("bodha.intake")
INTAKE_AGENT = "bodha-intake"
INTAKE_DONE = "intake processed"
PDF_SUFFIX = ".pdf"
PDF_TYPE = "application/pdf"
REASON_TYPE = "text/plain; charset=utf-8"
DAY_FOLDER = re.compile(r"^\d{4}-\d{2}-\d{2}$")
KEPT_SUFFIX = re.compile(r"^\.[a-z0-9]{1,8}$")
LAYOUT = "files go in <provider folder>/<YYYY-MM-DD>/<file>.pdf"
ALREADY_UPLOADED = "this PDF was already uploaded"


@dataclass(frozen=True)
class InboxGroup:
    folder: str
    provider_id: str
    service_date: date
    keys: tuple[str, ...]


@dataclass(frozen=True)
class InboxSort:
    groups: tuple[InboxGroup, ...]
    rejects: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class Stamp:
    inbox: str
    at: datetime
    day: date


@dataclass(frozen=True)
class IntakeRun:
    actor: Actor
    config: IntakeConfig
    stamp: Stamp


async def poll_intake(db: AsyncSession, store: ListingStore, now: datetime) -> int:
    if now.tzinfo is None:
        raise ValueError("now needs a time zone")
    created = 0
    for practice in await _intake_practices(db, now):
        created += await _locked_poll(db, store, practice, now)
    return created


def sort_inbox(inbox: str, keys: Sequence[str], config: IntakeConfig, today: date) -> InboxSort:
    grouped: dict[tuple[str, date], list[str]] = {}
    rejects: list[tuple[str, str]] = []
    for key in keys:
        relative = key[len(inbox) :] if key.startswith(inbox) else ""
        parts = relative.split("/")
        if not relative or relative.endswith("/") or parts[0] in (PROCESSED, REJECTED):
            continue
        problem = _placement_problem(parts, config, today)
        if problem is not None:
            rejects.append((key, problem))
            continue
        grouped.setdefault((parts[0], date.fromisoformat(parts[1])), []).append(key)
    groups = tuple(
        InboxGroup(folder, config.provider_by_folder[folder], day, tuple(sorted(found)))
        for (folder, day), found in sorted(grouped.items())
    )
    return InboxSort(groups, tuple(rejects))


def _placement_problem(parts: list[str], config: IntakeConfig, today: date) -> str | None:
    if len(parts) != 3 or not all(parts):
        return LAYOUT
    folder, day_text, name = parts
    if folder not in config.provider_by_folder:
        return f"no provider is set for the folder {folder}"
    day = _day(day_text)
    if day is None:
        return f"{day_text} is not a date (YYYY-MM-DD)"
    if day > today:
        return f"the date of service {day_text} is in the future"
    if not name.lower().endswith(PDF_SUFFIX):
        return "only PDF files are read"
    return None


def _day(text: str) -> date | None:
    if DAY_FOLDER.fullmatch(text) is None:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


async def _intake_practices(db: AsyncSession, now: datetime) -> list[Practice]:
    rows = (
        await db.scalars(
            select(Practice)
            .where(Practice.status.in_(ACTIVE_PRACTICE_STATUSES), Practice.intake["enabled"].as_boolean().is_(True))
            .order_by(Practice.created_at, Practice.id)
        )
    ).all()
    return [
        practice
        for practice in rows
        if practice.renews_on is None or practice.renews_on >= now.astimezone(zone_named(practice.time_zone)).date()
    ]


async def _locked_poll(db: AsyncSession, store: ListingStore, practice: Practice, now: datetime) -> int:
    engine = db.bind
    if not isinstance(engine, AsyncEngine):
        raise RuntimeError("intake needs a session bound to an engine")
    async with engine.connect() as guard:
        lock = func.pg_try_advisory_xact_lock(func.hashtextextended(f"intake:{practice.id}", 0))
        if not await guard.scalar(select(lock)):
            return 0
        return await _poll_practice(db, store, practice, now)


async def _poll_practice(db: AsyncSession, store: ListingStore, practice: Practice, now: datetime) -> int:
    actor = await _intake_actor(db, practice)
    if actor is None:
        logger.warning("intake for practice %s skipped: no active admin", practice.id)
        return 0
    config = intake_config(practice)
    inbox = inbox_prefix(practice.id, config)
    stamp = Stamp(inbox, now, now.astimezone(actor.zone).date())
    found = sort_inbox(inbox, await store.list_keys(inbox), config, stamp.day)
    if not found.groups and not found.rejects:
        return 0
    counts: Counter[str] = Counter(rejected=len(found.rejects))
    for key, reason in found.rejects:
        await _reject(store, stamp, key, await store.get(key), reason)
    run = IntakeRun(actor, config, stamp)
    for group in found.groups:
        counts += await _ingest(db, store, run, group)
    detail = f"{counts['created']} notes, {counts['rejected']} files rejected"
    record_activity(db, None, INTAKE_DONE, practice_id=practice.id, detail=detail)
    await db.commit()
    return counts["created"]


async def _intake_actor(db: AsyncSession, practice: Practice) -> Actor | None:
    admin = await db.scalar(
        select(User)
        .where(User.practice_id == practice.id, User.role == "admin", User.status == "active")
        .order_by(User.created_at, User.id)
        .limit(1)
    )
    return Actor(admin, practice, None, INTAKE_AGENT) if admin is not None else None


async def _ingest(db: AsyncSession, store: ListingStore, run: IntakeRun, group: InboxGroup) -> Counter[str]:
    ready: list[tuple[str, UploadFile]] = []
    counts: Counter[str] = Counter()
    for key in group.keys:
        file = UploadFile(PurePosixPath(key).name, await store.get(key), None, None)
        problem = _file_problem(file)
        if problem is None:
            ready.append((key, file))
            continue
        await _reject(store, run.stamp, key, file.data, problem)
        counts["rejected"] += 1
    if ready:
        counts += await _upload_group(db, store, run, group, ready)
    return counts


async def _upload_group(
    db: AsyncSession, store: ListingStore, run: IntakeRun, group: InboxGroup, ready: list[tuple[str, UploadFile]]
) -> Counter[str]:
    plan = UploadPlan(group.provider_id, group.service_date, run.config.place_code or "", run.config.visit_type)
    try:
        result = await create_upload(db, store, run.actor, plan, [file for _, file in ready])
    except AppError as error:
        for key, file in ready:
            await _reject(store, run.stamp, key, file.data, error.message)
        return Counter(rejected=len(ready))
    duplicates = set(result.duplicates)
    for key, file in ready:
        if file.name in duplicates:
            await _reject(store, run.stamp, key, file.data, ALREADY_UPLOADED)
        else:
            await _keep(store, run.stamp, key, file.data)
    return Counter(created=len(result.accepted), rejected=len(duplicates))


def _file_problem(file: UploadFile) -> str | None:
    try:
        check_pdf(file.name, file.data)
        billed_codes_for(file)
    except Invalid as error:
        return error.message
    return None


def _target(stamp: Stamp, folder: str, key: str, data: bytes) -> str:
    suffix = PurePosixPath(key).suffix.lower()
    kept = suffix if KEPT_SUFFIX.fullmatch(suffix) else ""
    return f"{stamp.inbox}{folder}/{stamp.day.isoformat()}/{hashlib.sha256(data).hexdigest()}{kept}"


async def _keep(store: ListingStore, stamp: Stamp, key: str, data: bytes) -> None:
    await store.put(_target(stamp, PROCESSED, key, data), data, content_type=PDF_TYPE)
    await store.delete([key])


async def _reject(store: ListingStore, stamp: Stamp, key: str, data: bytes, reason: str) -> None:
    target = _target(stamp, REJECTED, key, data)
    kind = PDF_TYPE if key.lower().endswith(PDF_SUFFIX) else "application/octet-stream"
    await store.put(target, data, content_type=kind)
    note = f"file: {key[len(stamp.inbox) :]}\nreason: {reason}\nat: {stamp.at.isoformat()}\n"
    await store.put(f"{target}.reason.txt", note.encode("utf-8"), content_type=REASON_TYPE)
    await store.delete([key])
