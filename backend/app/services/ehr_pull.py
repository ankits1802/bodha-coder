from __future__ import annotations

import logging
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from datetime import time as day_time

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.fhir_client import FhirClient, next_link
from app.adapters.guarded_http import OutboundError, OutboundHttp
from app.adapters.object_store import ObjectStore
from app.codes.clinical_notes import LOINC_SYSTEM, loinc_codes_for
from app.codes.npi import is_valid_npi
from app.codes.places import SETTING_BY_PLACE
from app.core.calendar import zone_named
from app.core.config import get_settings
from app.core.db import try_advisory_lock
from app.core.deps import ACTIVE_PRACTICE_STATUSES
from app.core.errors import Unavailable
from app.models import PULL_REASONS, EhrConnection, EhrDocument, EhrKey, EhrPullRun, Practice, utcnow
from app.services.ehr_documents import ACCEPTED, DUPLICATE, Directory, Shelf, take_document
from app.services.ehr_keys import current_key, ehr_ready, smart_client
from app.services.ehr_resources import DocumentReference, documents_in, fhir_day, fhir_id, is_wanted
from app.services.ehr_settings import latest_connection
from app.services.intake import accepts_intake
from app.services.intake_settings import intake_config
from app.services.upload_preview import active_places, active_providers

__all__ = [
    "EHR_PULL_LOCK",
    "MAX_DOCUMENTS",
    "MAX_PAGES",
    "PAGE_SIZE",
    "PULL_EVERY",
    "RUN_SECONDS",
    "SETTLE",
    "WINDOW",
    "poll_ehr_connections",
    "pull_practice",
    "search_params",
]

logger = logging.getLogger("bodha.ehr")
EHR_PULL_LOCK = "ehr pull"
PULL_EVERY = timedelta(minutes=15)
SETTLE = timedelta(minutes=2)
WINDOW = timedelta(days=7)
PAGE_SIZE = 50
MAX_PAGES = 200
MAX_DOCUMENTS = 200
RUN_SECONDS = 600
CURSOR_CANDIDATES = 50
FALLBACK_REASON = "server_error"
KEY_REASON = "no_key"


@dataclass
class Tally:
    deadline: float
    clock: Callable[[], float] = time.monotonic
    pages: int = 0
    accepted: int = 0
    duplicates: int = 0
    refused: int = 0
    skipped: int = 0
    stopped: bool = False

    def count(self, outcome: str) -> None:
        if outcome == ACCEPTED:
            self.accepted += 1
        elif outcome == DUPLICATE:
            self.duplicates += 1
        else:
            self.refused += 1

    def exhausted(self) -> bool:
        documents = self.accepted + self.duplicates + self.refused
        spent = documents >= MAX_DOCUMENTS or self.pages >= MAX_PAGES or self.clock() >= self.deadline
        self.stopped = self.stopped or spent
        return self.stopped


@dataclass(frozen=True)
class Ending:
    outcome: str
    reason: str | None = None
    cursor: datetime | None = None


@dataclass(frozen=True)
class Pull:
    db: AsyncSession
    store: ObjectStore
    http: OutboundHttp
    practice: Practice
    run: EhrPullRun
    connection: EhrConnection
    key: EhrKey


@dataclass
class Window:
    connection: EhrConnection
    codes: frozenset[str]
    seen: set[tuple[str, str]] = field(default_factory=set)


async def poll_ehr_connections(db: AsyncSession, store: ObjectStore, http: OutboundHttp, now: datetime) -> int:
    if now.tzinfo is None:
        raise ValueError("now needs a time zone")
    if not ehr_ready():
        return 0
    accepted = 0
    for practice_id in await _due_practices(db, now):
        try:
            accepted += await _locked_pull(db, store, http, practice_id, now)
        except Exception:
            await db.rollback()
            logger.exception("EHR pull for practice %s failed", practice_id)
    return accepted


async def pull_practice(
    db: AsyncSession, store: ObjectStore, http: OutboundHttp, practice_id: str, now: datetime
) -> int:
    practice = await db.get_one(Practice, practice_id)
    connection = await latest_connection(db, practice_id)
    key = await current_key(db, practice_id)
    if connection is None or connection.paused or key is None or not accepts_intake(practice, now):
        return 0
    run = EhrPullRun(practice_id=practice_id, connection_id=connection.id, since=await _cursor(db, connection))
    db.add(run)
    await db.commit()
    run_id, tally = run.id, Tally(time.monotonic() + RUN_SECONDS)
    try:
        ending = await _pull(Pull(db, store, http, practice, run, connection, key), tally, now)
    except OutboundError as error:
        await db.rollback()
        ending = Ending("failed", error.reason if error.reason in PULL_REASONS else FALLBACK_REASON)
    except Unavailable:
        await db.rollback()
        ending = Ending("failed", KEY_REASON)
    await _finish(db, run_id, ending, tally)
    return tally.accepted


def search_params(connection: EhrConnection, start: datetime, end: datetime) -> list[tuple[str, str]]:
    codes = sorted(loinc_codes_for(connection.note_types))
    return [
        ("status", "current"),
        ("type", ",".join(f"{LOINC_SYSTEM}|{code}" for code in codes)),
        ("date", f"ge{connection.start_date.isoformat()}"),
        ("_lastUpdated", f"ge{_instant(start)}"),
        ("_lastUpdated", f"lt{_instant(end)}"),
        ("_count", str(PAGE_SIZE)),
    ]


async def _locked_pull(
    db: AsyncSession, store: ObjectStore, http: OutboundHttp, practice_id: str, now: datetime
) -> int:
    async with try_advisory_lock(db, f"{EHR_PULL_LOCK}:{practice_id}") as held:
        return await pull_practice(db, store, http, practice_id, now) if held else 0


async def _pull(pull: Pull, tally: Tally, now: datetime) -> Ending:
    directory = await _directory(pull.db, pull.practice, now)
    client = smart_client(pull.connection, pull.key)
    async with pull.http.connect() as guarded:
        fhir = FhirClient(guarded, pull.connection.base_url, client)
        shelf = Shelf(pull.db, pull.store, fhir, pull.practice, pull.run, directory)
        window = Window(pull.connection, loinc_codes_for(pull.connection.note_types))
        cursor = await _walk(shelf, window, now, tally)
    return Ending("partial" if tally.stopped else "succeeded", None, cursor)


async def _walk(shelf: Shelf, window: Window, now: datetime, tally: Tally) -> datetime | None:
    cursor = shelf.run.since
    start = cursor or _day_start(window.connection.start_date, shelf.directory)
    until = now - SETTLE
    while start < until and not tally.exhausted():
        end = min(start + WINDOW, until)
        if not await _window(shelf, window, (start, end), tally):
            break
        cursor = start = end
    return cursor


async def _window(shelf: Shelf, window: Window, span: tuple[datetime, datetime], tally: Tally) -> bool:
    url: str | None = shelf.fhir.search_url("DocumentReference", search_params(window.connection, *span))
    while url is not None:
        if tally.exhausted():
            return False
        bundle = await shelf.fhir.bundle(url)
        tally.pages += 1
        if not await _page(shelf, window, list(documents_in(bundle)), tally):
            return False
        url = next_link(bundle)
    return True


async def _page(shelf: Shelf, window: Window, found: list[DocumentReference | None], tally: Tally) -> bool:
    readable = [document for document in found if document is not None and fhir_id(document.id)]
    tally.skipped += len(found) - len(readable)
    window.seen |= await _recorded(shelf, window.connection.base_url, readable)
    for document in readable:
        marker = (document.id, document.version)
        if marker in window.seen:
            continue
        if not _wanted(document, window, shelf.directory):
            window.seen.add(marker)
            tally.skipped += 1
            continue
        if tally.exhausted():
            return False
        window.seen.add(marker)
        tally.count(await take_document(shelf, document))
    return True


def _wanted(document: DocumentReference, window: Window, directory: Directory) -> bool:
    if not is_wanted(document, window.codes):
        return False
    written = fhir_day(document.date, directory.zone) if document.date else None
    return written is None or written >= window.connection.start_date


async def _recorded(shelf: Shelf, base_url: str, documents: Sequence[DocumentReference]) -> set[tuple[str, str]]:
    ids = sorted({document.id for document in documents})
    if not ids:
        return set()
    rows = await shelf.db.execute(
        select(EhrDocument.document_id, EhrDocument.document_version)
        .join(EhrPullRun, EhrPullRun.id == EhrDocument.run_id)
        .join(EhrConnection, EhrConnection.id == EhrPullRun.connection_id)
        .where(
            EhrDocument.practice_id == shelf.practice.id,
            EhrConnection.base_url == base_url,
            EhrDocument.document_id.in_(ids),
        )
    )
    return set(rows.tuples().all())


async def _cursor(db: AsyncSession, connection: EhrConnection) -> datetime | None:
    rows = await db.execute(
        select(EhrPullRun.cursor, EhrConnection.start_date, EhrConnection.note_types)
        .join(EhrConnection, EhrConnection.id == EhrPullRun.connection_id)
        .where(
            EhrPullRun.practice_id == connection.practice_id,
            EhrPullRun.cursor.is_not(None),
            EhrConnection.base_url == connection.base_url,
        )
        .order_by(EhrPullRun.created_at.desc(), EhrPullRun.id)
        .limit(CURSOR_CANDIDATES)
    )
    scope = (connection.start_date, list(connection.note_types))
    return next((cursor for cursor, start, types in rows.tuples() if (start, list(types)) == scope), None)


async def _due_practices(db: AsyncSession, now: datetime) -> list[str]:
    latest = (
        select(EhrConnection.practice_id, func.max(EhrConnection.revision).label("revision"))
        .group_by(EhrConnection.practice_id)
        .subquery()
    )
    practices = (
        await db.scalars(
            select(Practice)
            .join(latest, latest.c.practice_id == Practice.id)
            .join(
                EhrConnection,
                and_(EhrConnection.practice_id == Practice.id, EhrConnection.revision == latest.c.revision),
            )
            .join(EhrKey, and_(EhrKey.practice_id == Practice.id, EhrKey.retired_at.is_(None)))
            .where(EhrConnection.paused.is_(False), Practice.status.in_(ACTIVE_PRACTICE_STATUSES))
            .order_by(Practice.created_at, Practice.id)
        )
    ).all()
    last = await db.execute(
        select(EhrPullRun.practice_id, func.max(EhrPullRun.created_at)).group_by(EhrPullRun.practice_id)
    )
    started = dict(last.tuples().all())
    return [
        practice.id
        for practice in practices
        if accepts_intake(practice, now) and (practice.id not in started or started[practice.id] <= now - PULL_EVERY)
    ]


async def _directory(db: AsyncSession, practice: Practice, now: datetime) -> Directory:
    providers = await active_providers(db, practice.id)
    places = await active_places(db)
    config = intake_config(practice)
    zone = zone_named(practice.time_zone)
    return Directory(
        providers_by_npi={item.npi: item for item in providers if item.npi and is_valid_npi(item.npi)},
        places=frozenset(code for code in places if code in SETTING_BY_PLACE),
        fallback_place=config.place_code,
        visit_type=config.visit_type,
        zone=zone,
        today=now.astimezone(zone).date(),
        max_bytes=get_settings().max_upload_mb * 1024 * 1024,
    )


async def _finish(db: AsyncSession, run_id: str, ending: Ending, tally: Tally) -> None:
    run = await db.get_one(EhrPullRun, run_id, populate_existing=True)
    run.finished_at, run.outcome, run.reason, run.cursor = utcnow(), ending.outcome, ending.reason, ending.cursor
    run.pages, run.accepted, run.duplicates = tally.pages, tally.accepted, tally.duplicates
    run.refused, run.skipped = tally.refused, tally.skipped
    await db.commit()


def _instant(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _day_start(day: date, directory: Directory) -> datetime:
    return datetime.combine(day, day_time.min, tzinfo=directory.zone)
