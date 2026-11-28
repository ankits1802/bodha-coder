from __future__ import annotations

import asyncio
import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.object_store import ObjectStore, claim_export_key
from app.codes.ncci import NcciTables, ncci_tables
from app.core.deps import Actor
from app.core.errors import Conflict, Invalid, NotFound
from app.models import ApprovedClaim, ClaimExport, ClaimExportItem, Note, Provider, new_id, utcnow
from app.services.audit_log import record_access
from app.services.billing import ROW_LIMIT, billing_csv, billing_rows
from app.services.claim_holds import held_for_confirmation
from app.services.claim_lines import Claim, add_on_primaries, build_claim, claim_party, claims_csv, claims_json
from app.services.claim_snapshots import latest_snapshots, snapshot_codes
from app.services.worklists import count_of

__all__ = [
    "EXPORT_PAGE",
    "ExportedFile",
    "approved_unexported",
    "export_claim_lines",
    "export_csv",
    "export_page",
    "export_view",
    "mark_exported",
    "note_exports",
    "stored_export",
]

EXPORT_PAGE = 50
AGENT_LENGTH = 300
HELD = "a visit waiting for the provider to confirm its level cannot be exported"
FILES = {
    "csv": ("csv", "text/csv", "bodha-claims"),
    "claim_lines_csv": ("csv", "text/csv", "bodha-claim-lines"),
    "claim_lines_json": ("json", "application/json", "bodha-claim-lines"),
}


@dataclass(frozen=True)
class ExportedFile:
    export: ClaimExport
    content: bytes
    media_type: str


@dataclass(frozen=True)
class ExportedNote:
    note_id: str
    snapshot_id: str
    snapshot_revision: int


async def export_csv(
    db: AsyncSession, store: ObjectStore, actor: Actor, note_ids: list[str] | None, *, again: bool = False
) -> ExportedFile:
    if again and not note_ids:
        raise Invalid("choose the visits to download again")
    rows = [row for row in await billing_rows(db, actor.practice_id, exported=again) if _wanted(row["id"], note_ids)]
    if not again:
        rows = _unheld(rows, {row["id"] for row in rows if row["held"]}, named=note_ids is not None)
    if not rows:
        raise Invalid("nothing to export")
    notes = [ExportedNote(row["id"], row["snapshot_id"], row["snapshot_revision"]) for row in rows]
    exported = await _record(db, store, actor, "csv", notes=notes, content=billing_csv(rows).encode(), again=again)
    if not again:
        await mark_exported(db, [row["id"] for row in rows])
    action = "downloaded an export again" if again else "exported claims"
    record_access(db, actor, action, detail=_detail(len(rows), exported.export))
    await db.commit()
    return exported


async def export_claim_lines(
    db: AsyncSession, store: ObjectStore, actor: Actor, note_ids: list[str] | None, *, as_json: bool
) -> ExportedFile:
    query = approved_unexported(actor.practice_id)
    if note_ids is not None:
        query = query.where(Note.id.in_(note_ids))
    found = list((await db.execute(query)).all())
    held = await held_for_confirmation(db, [note.id for note, _ in found])
    rows = _unheld(found, held, named=note_ids is not None, key=lambda row: row[0].id)
    if not rows:
        raise Invalid("no approved visits are waiting for export")
    snapshots = await latest_snapshots(db, [note.id for note, _ in rows])
    tables = await asyncio.to_thread(ncci_tables)
    claims = [_snapshot_claim(tables, note, provider, snapshots.get(note.id)) for note, provider in rows]
    notes = [ExportedNote(note.id, snapshots[note.id].id, snapshots[note.id].revision) for note, _ in rows]
    content = json.dumps(claims_json(claims)) if as_json else claims_csv(claims)
    file_format = "claim_lines_json" if as_json else "claim_lines_csv"
    exported = await _record(db, store, actor, file_format, notes=notes, content=content.encode(), again=False)
    await mark_exported(db, [note.id for note, _ in rows])
    record_access(db, actor, "built claim lines", detail=_detail(len(rows), exported.export))
    await db.commit()
    return exported


async def export_page(db: AsyncSession, actor: Actor, offset: int) -> dict[str, Any]:
    query = select(ClaimExport).where(ClaimExport.practice_id == actor.practice_id)
    rows = await db.scalars(query.order_by(ClaimExport.created_at.desc()).offset(offset).limit(EXPORT_PAGE))
    items = [export_view(row) for row in rows]
    record_access(db, actor, "listed exports", detail=f"{len(items)} rows from {offset}")
    await db.commit()
    return {"items": items, "total": await count_of(db, query), "offset": offset, "page_size": EXPORT_PAGE}


async def stored_export(db: AsyncSession, store: ObjectStore, actor: Actor, export_id: str) -> ExportedFile:
    row = await db.get(ClaimExport, export_id)
    if row is None or row.practice_id != actor.practice_id:
        raise NotFound("export not found")
    content = await store.get(row.file_key)
    if hashlib.sha256(content).hexdigest() != row.file_sha256:
        raise Conflict(f"the stored file of export {row.id} does not match its recorded SHA-256")
    record_access(db, actor, "downloaded stored export", detail=f"export {row.id[:8]} · {row.notes_count} visits")
    await db.commit()
    return ExportedFile(row, content, FILES[row.format][1])


async def note_exports(db: AsyncSession, note_id: str) -> list[tuple[ClaimExport, ClaimExportItem]]:
    rows = await db.execute(
        select(ClaimExport, ClaimExportItem)
        .join(ClaimExportItem, ClaimExportItem.export_id == ClaimExport.id)
        .where(ClaimExportItem.note_id == note_id)
        .order_by(ClaimExport.created_at)
    )
    return [(export, item) for export, item in rows.all()]


def _wanted(note_id: str, note_ids: list[str] | None) -> bool:
    return note_ids is None or note_id in note_ids


def _unheld(rows: Sequence[Any], held: set[str], *, named: bool, key: Any = None) -> list[Any]:
    identify = key or (lambda row: row["id"])
    if named and any(identify(row) in held for row in rows):
        raise Conflict(HELD)
    return [row for row in rows if identify(row) not in held]


def _snapshot_claim(tables: NcciTables, note: Note, provider: Provider, snapshot: ApprovedClaim | None) -> Claim:
    if snapshot is None:
        raise Conflict(f"note {note.id} has no approved claim snapshot; reopen and approve it again")
    codes = snapshot_codes(snapshot)
    return build_claim(claim_party(note, provider), codes, primaries=add_on_primaries(tables, codes, note.service_date))


async def _record(
    db: AsyncSession,
    store: ObjectStore,
    actor: Actor,
    file_format: str,
    *,
    notes: list[ExportedNote],
    content: bytes,
    again: bool,
) -> ExportedFile:
    suffix, media_type, stem = FILES[file_format]
    export_id = new_id()
    key = claim_export_key(actor.practice_id, export_id, suffix)
    await store.put(key, content, content_type=media_type)
    export = ClaimExport(
        id=export_id,
        practice_id=actor.practice_id,
        format=file_format,
        again=again,
        file_key=key,
        file_name=f"{stem}-{_stamp(utcnow())}.{suffix}",
        file_sha256=hashlib.sha256(content).hexdigest(),
        file_bytes=len(content),
        notes_count=len(notes),
        **_exporter(actor),
    )
    db.add(export)
    await db.flush()
    db.add_all(_items(actor.practice_id, export_id, notes))
    return ExportedFile(export, content, media_type)


def _exporter(actor: Actor) -> dict[str, Any]:
    return {
        "actor_id": actor.user.id,
        "actor_name": actor.user.name,
        "actor_role": actor.role,
        "ip": actor.ip,
        "user_agent": (actor.user_agent or "")[:AGENT_LENGTH] or None,
    }


def _items(practice_id: str, export_id: str, notes: list[ExportedNote]) -> list[ClaimExportItem]:
    return [
        ClaimExportItem(
            practice_id=practice_id,
            export_id=export_id,
            note_id=item.note_id,
            approved_claim_id=item.snapshot_id,
            snapshot_revision=item.snapshot_revision,
        )
        for item in notes
    ]


def approved_unexported(practice_id: str) -> Select[tuple[Note, Provider]]:
    return (
        select(Note, Provider)
        .join(Provider, Provider.id == Note.provider_id)
        .where(Note.practice_id == practice_id, Note.status == "approved", Note.exported_at.is_(None))
        .order_by(Note.service_date, Note.approved_at)
        .limit(ROW_LIMIT)
    )


async def mark_exported(db: AsyncSession, note_ids: list[str]) -> None:
    stamp = utcnow()
    for note in (await db.scalars(select(Note).where(Note.id.in_(note_ids)))).all():
        note.status, note.exported_at = "exported", stamp


def _stamp(moment: datetime) -> str:
    return moment.strftime("%Y%m%d-%H%M")


def _detail(visits: int, export: ClaimExport) -> str:
    return f"{visits} visits · export {export.id[:8]} · sha256 {export.file_sha256[:12]}"


def export_view(row: ClaimExport) -> dict[str, Any]:
    return {
        "id": row.id,
        "at": row.created_at.isoformat(),
        "by": row.actor_name,
        "role": row.actor_role,
        "format": row.format,
        "again": row.again,
        "notes": row.notes_count,
        "file_name": row.file_name,
        "sha256": row.file_sha256,
        "bytes": row.file_bytes,
    }
