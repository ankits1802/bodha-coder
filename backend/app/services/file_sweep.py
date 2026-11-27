from __future__ import annotations

import logging
import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.adapters.object_listing import ListingStore, StoredObject
from app.adapters.object_store import note_document_key, note_document_revision_key, practice_prefix
from app.models import Activity, Analysis, EvalRun, Note, NoteText, Practice, Remittance
from app.services.intake_settings import INBOX_NAME
from app.services.records import PRACTICE_DELETED

__all__ = ["INTAKE", "ORPHAN_AGE", "PRACTICES_ROOT", "UNKNOWN", "StoredFile", "classify_key", "sweep_orphan_files"]

logger = logging.getLogger("bodha.files")
ORPHAN_AGE = timedelta(hours=24)
PRACTICES_ROOT = "practices/"
SWEEP_LOCK = "orphan file sweep"
DOCUMENT, REPLY, REMITTANCE, EVALUATION = "document", "reply", "remittance", "evaluation"
INTAKE, UNKNOWN = "intake", "unknown"
KEY_SHAPES = (
    (DOCUMENT, re.compile(r"^notes/(?P<owner>[^/]+)/document(?:-r(?P<detail>[1-9]\d*))?\.pdf$")),
    (REPLY, re.compile(r"^notes/(?P<owner>[^/]+)/analyses/(?P<detail>\d+)\.json$")),
    (REMITTANCE, re.compile(r"^remittances/(?P<owner>[^/]+)\.835$")),
    (EVALUATION, re.compile(r"^evaluations/(?P<owner>[^/]+)/(?P<detail>[^/]+)-\d+\.json$")),
)


@dataclass(frozen=True)
class StoredFile:
    key: str
    kind: str
    owner: str
    detail: str | None


async def sweep_orphan_files(db: AsyncSession, store: ListingStore, now: datetime) -> int:
    if now.tzinfo is None:
        raise ValueError("now needs a time zone")
    engine = db.bind
    if not isinstance(engine, AsyncEngine):
        raise RuntimeError("the sweep needs a session bound to an engine")
    async with engine.connect() as guard:
        if not await guard.scalar(select(func.pg_try_advisory_xact_lock(func.hashtextextended(SWEEP_LOCK, 0)))):
            return 0
        counts = await _sweep(db, store, now - ORPHAN_AGE)
    logger.info("orphan file sweep", extra={"fields": {key: counts[key] for key in sorted(counts)}})
    return counts["deleted"]


def classify_key(practice_id: str, key: str) -> StoredFile:
    prefix = practice_prefix(practice_id)
    relative = key[len(prefix) :] if key.startswith(prefix) else ""
    if INBOX_NAME.fullmatch(relative.split("/")[0]):
        return StoredFile(key, INTAKE, "", None)
    for kind, shape in KEY_SHAPES:
        found = shape.fullmatch(relative)
        if found is not None:
            return StoredFile(key, kind, found["owner"], found.groupdict().get("detail"))
    return StoredFile(key, UNKNOWN, "", None)


async def _sweep(db: AsyncSession, store: ListingStore, cutoff: datetime) -> Counter[str]:
    practices = set((await db.scalars(select(Practice.id))).all())
    counts: Counter[str] = Counter()
    for folder in await store.list_folders(PRACTICES_ROOT):
        practice_id = folder[len(PRACTICES_ROOT) : -1]
        if practice_id in practices:
            counts += await _sweep_practice(db, store, practice_id, cutoff)
        elif await _was_deleted(db, practice_id):
            counts += await _sweep_deleted_practice(store, folder, cutoff)
        else:
            counts["unknown_folders"] += 1
        await db.rollback()
    return counts


async def _sweep_practice(db: AsyncSession, store: ListingStore, practice_id: str, cutoff: datetime) -> Counter[str]:
    counts: Counter[str] = Counter()
    async for page in store.object_pages(practice_prefix(practice_id)):
        files = _settled_files(practice_id, page, cutoff, counts)
        held = await _held_keys(db, practice_id, files)
        orphans = [file.key for file in files if file.key not in held]
        await store.delete(orphans)
        counts["deleted"] += len(orphans)
        counts["kept"] += len(files) - len(orphans)
    return counts


def _settled_files(
    practice_id: str, page: Sequence[StoredObject], cutoff: datetime, counts: Counter[str]
) -> list[StoredFile]:
    files: list[StoredFile] = []
    for item in page:
        if item.modified >= cutoff:
            counts["recent"] += 1
            continue
        found = classify_key(practice_id, item.key)
        if found.kind in (INTAKE, UNKNOWN):
            counts[found.kind] += 1
        else:
            files.append(found)
    return files


async def _held_keys(db: AsyncSession, practice_id: str, files: list[StoredFile]) -> set[str]:
    def of(*kinds: str) -> list[StoredFile]:
        return [file for file in files if file.kind in kinds]

    return (
        await _held_note_files(db, practice_id, of(DOCUMENT, REPLY))
        | await _held_remittances(db, practice_id, of(REMITTANCE))
        | await _held_evaluations(db, practice_id, of(EVALUATION))
    )


async def _held_note_files(db: AsyncSession, practice_id: str, files: list[StoredFile]) -> set[str]:
    if not files:
        return set()
    owners = {file.owner for file in files}
    rows = await db.execute(select(Note.id, Note.file_key).where(Note.practice_id == practice_id, Note.id.in_(owners)))
    notes = dict(rows.all())
    if not notes:
        return set()
    ids = list(notes)
    texts = select(NoteText.note_id, NoteText.revision).where(NoteText.note_id.in_(ids), NoteText.source == "document")
    replies = select(Analysis.response_key).where(Analysis.note_id.in_(ids), Analysis.response_key.is_not(None))
    held = set(notes.values()) | set((await db.scalars(replies)).all())
    held |= {note_document_key(practice_id, note_id) for note_id in notes}
    revisions = (await db.execute(texts)).all()
    held |= {note_document_revision_key(practice_id, note_id, revision) for note_id, revision in revisions}
    return {file.key for file in files if file.key in held}


async def _held_remittances(db: AsyncSession, practice_id: str, files: list[StoredFile]) -> set[str]:
    if not files:
        return set()
    keys = [file.key for file in files]
    query = select(Remittance.file_key).where(Remittance.practice_id == practice_id, Remittance.file_key.in_(keys))
    return set((await db.scalars(query)).all())


async def _held_evaluations(db: AsyncSession, practice_id: str, files: list[StoredFile]) -> set[str]:
    if not files:
        return set()
    runs = {file.owner for file in files}
    query = select(EvalRun.id, EvalRun.results).where(EvalRun.practice_id == practice_id, EvalRun.id.in_(runs))
    rows = await db.execute(query)
    cases = {(run_id, result.get("case_id")) for run_id, results in rows for result in results or []}
    return {file.key for file in files if (file.owner, file.detail) in cases}


async def _was_deleted(db: AsyncSession, practice_id: str) -> bool:
    found = await db.scalar(
        select(Activity.id).where(Activity.practice_id == practice_id, Activity.action == PRACTICE_DELETED).limit(1)
    )
    return found is not None


async def _sweep_deleted_practice(store: ListingStore, folder: str, cutoff: datetime) -> Counter[str]:
    counts: Counter[str] = Counter()
    async for page in store.object_pages(folder):
        old = [item.key for item in page if item.modified < cutoff]
        await store.delete(old)
        counts["deleted"] += len(old)
        counts["recent"] += len(page) - len(old)
    return counts
