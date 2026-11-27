from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.object_store import ObjectStore, note_document_key
from app.codes.billing_codes import Code, FilenameFacts, parse_code_list, parse_note_filename
from app.codes.places import setting_for
from app.core.calendar import day_bounds, zone_named
from app.core.config import get_settings
from app.core.deps import Actor
from app.core.errors import Invalid, NotFound
from app.models import Batch, CodeSet, Note, PlaceOfService, Practice, Provider, User, new_id
from app.services.analysis import request_analysis
from app.services.audit_log import SystemActor, record_access, record_system_access

PDF_MAGIC = b"%PDF"
HISTORY_PAGE = 50
UPLOADED_NOTES = "uploaded notes"
UPLOAD_SOURCE = "upload"
INTAKE_SOURCE = "intake"
INTAKE_UPLOADER = "Intake"
INTAKE_ACTOR = SystemActor("bodha-intake", "Bodha intake")


@dataclass(frozen=True)
class UploadFile:
    name: str
    data: bytes
    billed: str | None
    visit_type: str | None


@dataclass(frozen=True)
class UploadPlan:
    provider_id: str
    service_date: date
    place_code: str
    visit_type: str


@dataclass(frozen=True)
class UploadResult:
    batch_id: str
    accepted: list[str]
    duplicates: list[str]

    def detail(self) -> str:
        return f"{len(self.accepted)} notes, batch {self.batch_id}"


@dataclass(frozen=True)
class Uploader:
    practice_id: str
    zone: ZoneInfo
    user_id: str | None
    source: str


def preview(file_names: list[str]) -> list[FilenameFacts]:
    return [parse_note_filename(name) for name in file_names]


def due_at(service_date: date, zone: ZoneInfo) -> datetime:
    _, day_after = day_bounds(service_date, zone)
    return day_after + timedelta(hours=get_settings().turnaround_hours)


def billed_codes_for(file: UploadFile) -> tuple[Code, ...]:
    text = file.billed if file.billed is not None else (parse_note_filename(file.name).cpt or "")
    parsed = parse_code_list(text)
    if parsed.invalid:
        raise Invalid(f"{file.name}: not valid codes: {', '.join(parsed.invalid)}")
    return parsed.codes


async def create_upload(
    db: AsyncSession, store: ObjectStore, actor: Actor, plan: UploadPlan, files: list[UploadFile]
) -> UploadResult:
    uploader = Uploader(actor.practice_id, actor.zone, actor.user.id, UPLOAD_SOURCE)
    result = await _store_batch(db, store, uploader, plan, files)
    record_access(db, actor, UPLOADED_NOTES, detail=result.detail())
    await db.commit()
    return result


async def create_intake_upload(
    db: AsyncSession, store: ObjectStore, practice: Practice, plan: UploadPlan, files: list[UploadFile]
) -> UploadResult:
    uploader = Uploader(practice.id, zone_named(practice.time_zone), None, INTAKE_SOURCE)
    result = await _store_batch(db, store, uploader, plan, files)
    record_system_access(db, INTAKE_ACTOR, practice.id, UPLOADED_NOTES, detail=result.detail())
    await db.commit()
    return result


async def _store_batch(
    db: AsyncSession, store: ObjectStore, uploader: Uploader, plan: UploadPlan, files: list[UploadFile]
) -> UploadResult:
    await _check_plan(db, uploader.practice_id, plan)
    if not files:
        raise Invalid("add at least one PDF")
    for file in files:
        check_pdf(file.name, file.data)
        billed_codes_for(file)
    batch = Batch(
        practice_id=uploader.practice_id,
        provider_id=plan.provider_id,
        service_date=plan.service_date,
        place_code=plan.place_code,
        visit_type=plan.visit_type,
        created_by=uploader.user_id,
        source=uploader.source,
    )
    db.add(batch)
    await db.flush()
    accepted, duplicates = [], []
    for file in files:
        note = await _add_note(db, store, uploader, batch, file)
        (accepted if note else duplicates).append(file.name)
    return UploadResult(batch.id, accepted, duplicates)


async def _check_plan(db: AsyncSession, practice_id: str, plan: UploadPlan) -> None:
    provider = await db.get(Provider, plan.provider_id)
    if provider is None or provider.practice_id != practice_id or not provider.active:
        raise NotFound("provider not found")
    place = await db.get(PlaceOfService, plan.place_code)
    if place is None or not place.active:
        raise Invalid("choose an active place of service")
    setting_for(plan.place_code)


async def _add_note(
    db: AsyncSession, store: ObjectStore, uploader: Uploader, batch: Batch, file: UploadFile
) -> Note | None:
    sha256 = hashlib.sha256(file.data).hexdigest()
    held = await db.scalar(select(Note.id).where(Note.practice_id == uploader.practice_id, Note.file_sha256 == sha256))
    if held is not None:
        return None
    billed = billed_codes_for(file)
    facts = parse_note_filename(file.name)
    note_id = new_id()
    key = note_document_key(uploader.practice_id, note_id)
    await store.put(key, file.data, content_type="application/pdf")
    note = Note(
        id=note_id,
        practice_id=uploader.practice_id,
        batch_id=batch.id,
        provider_id=batch.provider_id,
        file_key=key,
        file_name=file.name[:255],
        file_sha256=sha256,
        file_bytes=len(file.data),
        patient_name=facts.patient_name,
        service_date=batch.service_date,
        visit_type=file.visit_type or batch.visit_type,
        place_code=batch.place_code,
        due_at=due_at(batch.service_date, uploader.zone),
    )
    db.add(note)
    await db.flush()
    db.add(_billed_set(note_id, uploader, billed))
    await request_analysis(db, note, reason="upload")
    return note


def _billed_set(note_id: str, uploader: Uploader, billed: tuple[Code, ...]) -> CodeSet:
    return CodeSet(
        note_id=note_id,
        kind="billed",
        revision=1,
        reason="upload",
        actor_id=uploader.user_id,
        codes=[code.as_json() for code in billed],
    )


def check_pdf(name: str, data: bytes) -> None:
    if not data.startswith(PDF_MAGIC):
        raise Invalid(f"{name} is not a PDF")
    if len(data) > get_settings().max_upload_mb * 1024 * 1024:
        raise Invalid(f"{name} is larger than {get_settings().max_upload_mb} MB")


async def batch_history(db: AsyncSession, practice_id: str, *, offset: int) -> dict[str, Any]:
    filters = (Batch.practice_id == practice_id, exists().where(Note.batch_id == Batch.id))
    rows = (
        await db.execute(
            select(Batch, Provider.name, User.name)
            .join(Provider, Provider.id == Batch.provider_id)
            .outerjoin(User, User.id == Batch.created_by)
            .where(*filters)
            .order_by(Batch.created_at.desc(), Batch.id)
            .offset(offset)
            .limit(HISTORY_PAGE)
        )
    ).all()
    counts = await _status_counts(db, [batch.id for batch, _, _ in rows])
    return {
        "items": [
            _history_row(batch, provider, uploader, counts.get(batch.id, {})) for batch, provider, uploader in rows
        ],
        "total": await db.scalar(select(func.count()).select_from(Batch).where(*filters)) or 0,
        "offset": offset,
        "page_size": HISTORY_PAGE,
    }


async def _status_counts(db: AsyncSession, batch_ids: list[str]) -> dict[str, dict[str, int]]:
    if not batch_ids:
        return {}
    rows = await db.execute(
        select(Note.batch_id, Note.status, func.count())
        .where(Note.batch_id.in_(batch_ids))
        .group_by(Note.batch_id, Note.status)
    )
    found: dict[str, dict[str, int]] = {}
    for batch_id, status, count in rows:
        found.setdefault(batch_id, {})[status] = count
    return found


def _uploader_label(batch: Batch, user_name: str | None) -> str:
    if batch.source == INTAKE_SOURCE:
        return INTAKE_UPLOADER
    return user_name or ""


def _history_row(batch: Batch, provider: str, uploader: str | None, counts: dict[str, int]) -> dict[str, Any]:
    return {
        "id": batch.id,
        "provider_name": provider,
        "service_date": batch.service_date.isoformat(),
        "place_code": batch.place_code,
        "visit_type": batch.visit_type,
        "uploaded_by": _uploader_label(batch, uploader),
        "created_at": batch.created_at.isoformat(),
        "counts": counts,
    }
