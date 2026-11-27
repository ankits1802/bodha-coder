from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.object_store import ObjectStore, note_document_key, note_document_revision_key
from app.models import (
    AccessLog,
    AddendumRequest,
    Analysis,
    ApprovedClaim,
    Base,
    CodeSet,
    Decision,
    Note,
    NoteText,
    ProviderAttestation,
    Suggestion,
)
from app.services.claim_exports import note_exports
from app.services.review_comments import note_comment_rows

__all__ = ["PackageFile", "json_file", "note_files", "row_record"]

SECRET_COLUMNS = frozenset({"token_hash", "code_hash"})
WITHHELD = "withheld: the file also holds other patients' visits"


@dataclass(frozen=True)
class PackageFile:
    path: str
    content: bytes


def row_record(row: Base) -> dict[str, Any]:
    return {
        column.name: getattr(row, column.key) for column in row.__table__.columns if column.name not in SECRET_COLUMNS
    }


def json_file(path: str, value: Any) -> PackageFile:
    return PackageFile(path, json.dumps(value, indent=2, sort_keys=True, default=str).encode())


async def note_files(db: AsyncSession, store: ObjectStore, note: Note) -> list[PackageFile]:
    files = [*await _documents(db, store, note), *await _texts(db, note.id), *await _analyses(db, store, note.id)]
    for path, model, order in (
        ("suggestions.json", Suggestion, Suggestion.created_at),
        ("decisions.json", Decision, Decision.created_at),
        ("code-sets.json", CodeSet, CodeSet.created_at),
        ("snapshots.json", ApprovedClaim, ApprovedClaim.revision),
        ("provider-requests.json", AddendumRequest, AddendumRequest.created_at),
        ("provider-statements.json", ProviderAttestation, ProviderAttestation.created_at),
    ):
        rows = await db.scalars(select(model).where(model.note_id == note.id).order_by(order))
        files.append(json_file(path, [row_record(row) for row in rows]))
    files += await _exports(db, store, note.id)
    files.append(json_file("comments.json", await _comments(db, note.id)))
    files.append(json_file("access-log.json", await _access_log(db, note)))
    return files


async def _documents(db: AsyncSession, store: ObjectStore, note: Note) -> list[PackageFile]:
    revisions = await db.scalars(
        select(NoteText.revision).where(NoteText.note_id == note.id, NoteText.source == "document")
    )
    keys = [note_document_key(note.practice_id, note.id), note.file_key]
    keys += [note_document_revision_key(note.practice_id, note.id, revision) for revision in revisions]
    files = []
    for key in dict.fromkeys(keys):
        if await store.exists(key):
            files.append(PackageFile(f"documents/{key.rsplit('/', 1)[-1]}", await store.get(key)))
    return files


async def _texts(db: AsyncSession, note_id: str) -> list[PackageFile]:
    rows = await db.scalars(select(NoteText).where(NoteText.note_id == note_id).order_by(NoteText.revision))
    return [PackageFile(f"texts/r{row.revision}-{row.source}.txt", row.text.encode()) for row in rows]


async def _analyses(db: AsyncSession, store: ObjectStore, note_id: str) -> list[PackageFile]:
    rows = list(
        (await db.scalars(select(Analysis).where(Analysis.note_id == note_id).order_by(Analysis.revision))).all()
    )
    files = [json_file(f"analyses/run-{row.revision}.json", row_record(row)) for row in rows]
    seen: set[str] = set()
    for row in rows:
        key = row.response_key
        if key and key not in seen and await store.exists(key):
            seen.add(key)
            files.append(PackageFile(f"analyses/run-{row.revision}-replies.json", await store.get(key)))
    return files


async def _exports(db: AsyncSession, store: ObjectStore, note_id: str) -> list[PackageFile]:
    records, files = [], []
    for export, item in await note_exports(db, note_id):
        alone = export.notes_count == 1
        stored = f"exports/{export.id}.{export.file_key.rsplit('.', 1)[-1]}"
        if alone:
            files.append(PackageFile(stored, await store.get(export.file_key)))
        records.append({**row_record(export), "item": row_record(item), "file": stored if alone else WITHHELD})
    return [json_file("exports.json", records), *files]


async def _comments(db: AsyncSession, note_id: str) -> list[dict[str, Any]]:
    return [
        {**row_record(comment), "removal": row_record(removal) if removal else None}
        for comment, removal in await note_comment_rows(db, note_id)
    ]


async def _access_log(db: AsyncSession, note: Note) -> list[dict[str, Any]]:
    rows: Iterable[AccessLog] = await db.scalars(
        select(AccessLog)
        .where(AccessLog.note_id == note.id, AccessLog.practice_id == note.practice_id)
        .order_by(AccessLog.created_at)
    )
    return [row_record(row) for row in rows]
