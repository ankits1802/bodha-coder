from __future__ import annotations

import hashlib
import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import PurePosixPath

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.adapters.object_listing import ListingStore
from app.codes.billing_codes import parse_note_filename
from app.core.calendar import zone_named
from app.core.deps import ACTIVE_PRACTICE_STATUSES
from app.core.errors import AppError, Invalid
from app.models import Practice
from app.services.audit_log import record_activity
from app.services.intake_settings import PROCESSED, REJECTED, IntakeConfig, inbox_prefix, intake_config
from app.services.uploads import UploadFile, UploadPlan, billed_codes_for, check_pdf, create_intake_upload

__all__ = ["InboxGroup", "InboxSort", "arrival_name", "poll_intake", "sort_inbox"]

INTAKE_DONE = "intake processed"
PDF_SUFFIX = ".pdf"
PDF_TYPE = "application/pdf"
OTHER_TYPE = "application/octet-stream"
REASON_TYPE = "text/plain; charset=utf-8"
DAY_FOLDER = re.compile(r"^\d{4}-\d{2}-\d{2}$")
KEPT_SUFFIX = re.compile(r"^\.[a-z0-9]{1,8}$")
ARRIVAL_NAME = re.compile(r"^[0-9a-f]{64}( - [0-9A-Z]{5})?(\.[a-z0-9]{1,8})?$")
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
    practice: Practice
    config: IntakeConfig
    stamp: Stamp


async def poll_intake(db: AsyncSession, store: ListingStore, now: datetime) -> int:
    if now.tzinfo is None:
        raise ValueError("now needs a time zone")
    created = 0
    for practice in await _intake_practices(db, now):
        created += await _locked_poll(db, store, practice, now)
    return created


def arrival_name(name: str, data: bytes) -> str:
    suffix = PurePosixPath(name).suffix.lower()
    kept = suffix if KEPT_SUFFIX.fullmatch(suffix) else ""
    cpt = parse_note_filename(name).cpt if kept == PDF_SUFFIX else None
    coded = f" - {cpt}" if cpt else ""
    return f"{hashlib.sha256(data).hexdigest()}{coded}{kept}"


def sort_inbox(inbox: str, keys: Sequence[str], config: IntakeConfig, today: date) -> InboxSort:
    grouped: dict[tuple[str, date], list[str]] = {}
    rejects: list[tuple[str, str]] = []
    for key in keys:
        relative = _relative(inbox, key)
        if relative is None:
            continue
        parts = relative.split("/")
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


def _relative(inbox: str, key: str) -> str | None:
    relative = key[len(inbox) :] if key.startswith(inbox) else ""
    if not relative or relative.endswith("/") or relative.split("/")[0] in (PROCESSED, REJECTED):
        return None
    return relative


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
    config = intake_config(practice)
    inbox = inbox_prefix(practice.id, config)
    stamp = Stamp(inbox, now, now.astimezone(zone_named(practice.time_zone)).date())
    arrived = await _rename_arrivals(store, inbox, await store.list_keys(inbox))
    found = sort_inbox(inbox, arrived, config, stamp.day)
    if not found.groups and not found.rejects:
        return 0
    counts: Counter[str] = Counter(rejected=len(found.rejects))
    for key, reason in found.rejects:
        await _reject(store, stamp, key, await store.get(key), reason)
    run = IntakeRun(practice, config, stamp)
    for group in found.groups:
        counts += await _ingest(db, store, run, group)
    detail = f"{counts['created']} notes, {counts['rejected']} files rejected"
    record_activity(db, None, INTAKE_DONE, practice_id=practice.id, detail=detail)
    await db.commit()
    return counts["created"]


async def _rename_arrivals(store: ListingStore, inbox: str, keys: Sequence[str]) -> list[str]:
    arrived: set[str] = set()
    for key in keys:
        if _relative(inbox, key) is None:
            continue
        path = PurePosixPath(key)
        if ARRIVAL_NAME.fullmatch(path.name):
            arrived.add(key)
            continue
        data = await store.get(key)
        target = f"{path.parent}/{arrival_name(path.name, data)}"
        await store.put(target, data, content_type=_content_type(target))
        await store.delete([key])
        arrived.add(target)
    return sorted(arrived)


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
        result = await create_intake_upload(db, store, run.practice, plan, [file for _, file in ready])
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


def _content_type(key: str) -> str:
    return PDF_TYPE if key.lower().endswith(PDF_SUFFIX) else OTHER_TYPE


def _target(stamp: Stamp, folder: str, key: str, data: bytes) -> str:
    suffix = PurePosixPath(key).suffix.lower()
    kept = suffix if KEPT_SUFFIX.fullmatch(suffix) else ""
    return f"{stamp.inbox}{folder}/{stamp.day.isoformat()}/{hashlib.sha256(data).hexdigest()}{kept}"


async def _keep(store: ListingStore, stamp: Stamp, key: str, data: bytes) -> None:
    await store.put(_target(stamp, PROCESSED, key, data), data, content_type=PDF_TYPE)
    await store.delete([key])


async def _reject(store: ListingStore, stamp: Stamp, key: str, data: bytes, reason: str) -> None:
    target = _target(stamp, REJECTED, key, data)
    await store.put(target, data, content_type=_content_type(key))
    note = f"file: {key[len(stamp.inbox) :]}\nreason: {reason}\nat: {stamp.at.isoformat()}\n"
    await store.put(f"{target}.reason.txt", note.encode("utf-8"), content_type=REASON_TYPE)
    await store.delete([key])
