from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.object_store import ObjectStore, note_document_key
from app.codes.billing_codes import Code, FilenameFacts, parse_code_list, parse_note_filename
from app.codes.places import setting_for
from app.core.config import get_settings
from app.core.deps import Actor
from app.core.errors import Invalid, NotFound
from app.models import Batch, CodeSet, Note, PlaceOfService, Provider, new_id
from app.services.analysis import request_analysis
from app.services.audit_log import record_access

PDF_MAGIC = b"%PDF"


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


def preview(file_names: list[str]) -> list[FilenameFacts]:
    return [parse_note_filename(name) for name in file_names]


def due_at(service_date: date) -> datetime:
    day_after = datetime.combine(service_date + timedelta(days=1), time.min, UTC)
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
    await _check_plan(db, actor, plan)
    if not files:
        raise Invalid("add at least one PDF")
    for file in files:
        _check_pdf(file)
        billed_codes_for(file)
    batch = Batch(
        practice_id=actor.practice_id,
        provider_id=plan.provider_id,
        service_date=plan.service_date,
        place_code=plan.place_code,
        visit_type=plan.visit_type,
        created_by=actor.user.id,
    )
    db.add(batch)
    await db.flush()
    accepted, duplicates = [], []
    for file in files:
        note = await _add_note(db, store, actor, batch, file)
        (accepted if note else duplicates).append(file.name)
    record_access(db, actor, "uploaded notes", detail=f"{len(accepted)} notes, batch {batch.id}")
    await db.commit()
    return UploadResult(batch.id, accepted, duplicates)


async def _check_plan(db: AsyncSession, actor: Actor, plan: UploadPlan) -> None:
    provider = await db.get(Provider, plan.provider_id)
    if provider is None or provider.practice_id != actor.practice_id or not provider.active:
        raise NotFound("provider not found")
    place = await db.get(PlaceOfService, plan.place_code)
    if place is None or not place.active:
        raise Invalid("choose an active place of service")
    setting_for(plan.place_code)


async def _add_note(db: AsyncSession, store: ObjectStore, actor: Actor, batch: Batch, file: UploadFile) -> Note | None:
    sha256 = hashlib.sha256(file.data).hexdigest()
    exists = await db.scalar(select(Note.id).where(Note.practice_id == actor.practice_id, Note.file_sha256 == sha256))
    if exists is not None:
        return None
    billed = billed_codes_for(file)
    facts = parse_note_filename(file.name)
    note_id = new_id()
    key = note_document_key(actor.practice_id, note_id)
    await store.put(key, file.data, content_type="application/pdf")
    note = Note(
        id=note_id,
        practice_id=actor.practice_id,
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
        due_at=due_at(batch.service_date),
    )
    db.add(note)
    await db.flush()
    db.add(
        CodeSet(
            note_id=note_id,
            kind="billed",
            revision=1,
            reason="upload",
            actor_id=actor.user.id,
            codes=[code.as_json() for code in billed],
        )
    )
    await request_analysis(db, note, reason="upload")
    return note


def _check_pdf(file: UploadFile) -> None:
    if not file.data.startswith(PDF_MAGIC):
        raise Invalid(f"{file.name} is not a PDF")
    if len(file.data) > get_settings().max_upload_mb * 1024 * 1024:
        raise Invalid(f"{file.name} is larger than {get_settings().max_upload_mb} MB")
