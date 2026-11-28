from __future__ import annotations

import asyncio
import base64
import codecs
import hashlib
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.fhir_client import FhirClient, FhirMissing, FhirRefused, ForeignLink, decoded_data
from app.adapters.guarded_http import TooLarge
from app.adapters.note_pdf import html_text, text_note_pdf
from app.adapters.object_store import ObjectStore
from app.adapters.smart_backend import BadAnswer
from app.core.errors import AppError
from app.models import VOIDED, EhrDocument, EhrPullRun, Note, Practice
from app.services.ehr_resources import (
    HTML,
    PDF,
    READABLE_TYPES,
    Attachment,
    DocumentReference,
    Encounter,
    Practitioner,
    chosen_attachment,
    fhir_id,
    is_final,
    npi_of,
    place_for,
    practitioner_references,
    read_encounter,
    read_practitioner,
    reference_id,
    service_day,
)
from app.services.intake import arrival_name
from app.services.upload_matching import ProviderRef
from app.services.uploads import FHIR_SOURCE, OpenBatches, UploadFile, UploadPlan, file_problem, stage_intake_upload

__all__ = ["ACCEPTED", "DUPLICATE", "REFUSED", "Directory", "Refusal", "Shelf", "take_document"]

ACCEPTED = "accepted"
DUPLICATE = "duplicate"
REFUSED = "refused"
NOTE_NAME = "visit note.pdf"
DEFAULT_CHARSET = "utf-8"
MAX_PRACTITIONERS = 5
UNREACHABLE_PARTS = (FhirMissing, FhirRefused, BadAnswer)


class Refusal(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class Directory:
    providers_by_npi: Mapping[str, ProviderRef]
    places: frozenset[str]
    fallback_place: str | None
    visit_type: str
    zone: ZoneInfo
    today: date
    max_bytes: int


@dataclass
class Shelf:
    db: AsyncSession
    store: ObjectStore
    fhir: FhirClient
    practice: Practice
    run: EhrPullRun
    directory: Directory
    opened: OpenBatches = field(default_factory=dict)
    encounters: dict[str, Encounter | None] = field(default_factory=dict)
    practitioners: dict[str, Practitioner | None] = field(default_factory=dict)


@dataclass
class Trail:
    document: DocumentReference
    encounter_id: str | None = None
    practitioner_id: str | None = None


@dataclass(frozen=True)
class Placed:
    plan: UploadPlan
    file: UploadFile


async def take_document(shelf: Shelf, document: DocumentReference) -> str:
    trail = Trail(document)
    try:
        placed = await _placed(shelf, trail)
        outcome, note_id = await _stage(shelf, placed)
    except Refusal as refusal:
        await _record(shelf, trail, REFUSED, reason=refusal.reason)
        return REFUSED
    await _record(shelf, trail, outcome, note_id=note_id, file=placed.file)
    return outcome


async def _placed(shelf: Shelf, trail: Trail) -> Placed:
    document, directory = trail.document, shelf.directory
    if not is_final(document):
        raise Refusal("not_final")
    attachment = _attachment(document, directory.max_bytes)
    encounter = await _encounter(shelf, trail)
    day = service_day(encounter, document, directory.zone)
    if day is None:
        raise Refusal("no_service_date")
    if day > directory.today:
        raise Refusal("future_service_date")
    provider = await _provider(shelf, trail, encounter)
    place = place_for(encounter, provider.place_code, directory.places) or directory.fallback_place
    if not place or place not in directory.places:
        raise Refusal("no_place")
    pdf = await _pdf(shelf, attachment)
    file = UploadFile(arrival_name(NOTE_NAME, pdf), pdf, None, None)
    if file_problem(file) is not None:
        raise Refusal("file_refused")
    return Placed(UploadPlan(provider.id, day, place, directory.visit_type), file)


def _attachment(document: DocumentReference, max_bytes: int) -> Attachment:
    attachment = chosen_attachment(document)
    if attachment is None:
        raise Refusal("unsupported_format" if document.content else "no_attachment")
    if attachment.size is not None and attachment.size > max_bytes:
        raise Refusal("too_large")
    return attachment


async def _encounter(shelf: Shelf, trail: Trail) -> Encounter | None:
    context = trail.document.context
    reference = next(iter(context.encounter), None) if context else None
    trail.encounter_id = reference_id(reference, "Encounter")
    if reference is None or trail.encounter_id is None or reference.reference is None:
        return None
    if reference.reference not in shelf.encounters:
        resource = await _read(shelf, reference.reference, "Encounter")
        shelf.encounters[reference.reference] = read_encounter(resource) if resource else None
    return shelf.encounters[reference.reference]


async def _provider(shelf: Shelf, trail: Trail, encounter: Encounter | None) -> ProviderRef:
    for reference in practitioner_references(trail.document, encounter)[:MAX_PRACTITIONERS]:
        practitioner = await _practitioner(shelf, reference)
        if practitioner is None:
            continue
        trail.practitioner_id = trail.practitioner_id or fhir_id(practitioner.id)
        npi = npi_of(practitioner)
        if npi is not None and npi in shelf.directory.providers_by_npi:
            trail.practitioner_id = fhir_id(practitioner.id)
            return shelf.directory.providers_by_npi[npi]
    raise Refusal("no_provider")


async def _practitioner(shelf: Shelf, reference: str) -> Practitioner | None:
    if reference not in shelf.practitioners:
        resource = await _read(shelf, reference, "Practitioner")
        shelf.practitioners[reference] = read_practitioner(resource) if resource else None
    return shelf.practitioners[reference]


async def _read(shelf: Shelf, reference: str, resource_type: str) -> dict | None:
    try:
        return await shelf.fhir.read(reference, resource_type)
    except ForeignLink as error:
        raise Refusal("foreign_reference") from error
    except UNREACHABLE_PARTS:
        return None


async def _pdf(shelf: Shelf, attachment: Attachment) -> bytes:
    data, media_type = await _download(shelf, attachment)
    if attachment.hash and base64.b64encode(hashlib.sha1(data).digest()).decode() != attachment.hash.strip():
        raise Refusal("attachment_mismatch")
    if media_type == PDF:
        return data
    text = data.decode(_charset(attachment), errors="replace")
    try:
        return await asyncio.to_thread(text_note_pdf, html_text(text) if media_type == HTML else text)
    except ValueError as error:
        raise Refusal("file_refused") from error


async def _download(shelf: Shelf, attachment: Attachment) -> tuple[bytes, str]:
    limit = shelf.directory.max_bytes
    try:
        if attachment.data:
            return decoded_data(attachment.data, limit), attachment.media_type
        data, served = await shelf.fhir.attachment(attachment.url or "", attachment.media_type, max_bytes=limit)
    except TooLarge as error:
        raise Refusal("too_large") from error
    except ForeignLink as error:
        raise Refusal("foreign_reference") from error
    except UNREACHABLE_PARTS as error:
        raise Refusal("attachment_unavailable") from error
    return data, served if served in READABLE_TYPES else attachment.media_type


async def _stage(shelf: Shelf, placed: Placed) -> tuple[str, str]:
    sha256 = hashlib.sha256(placed.file.data).hexdigest()
    held = await _held_note(shelf, sha256)
    if held is not None:
        return DUPLICATE, held
    try:
        async with shelf.db.begin_nested():
            await stage_intake_upload(
                shelf.db,
                shelf.store,
                shelf.practice,
                [(placed.plan, [placed.file])],
                source=FHIR_SOURCE,
                opened=shelf.opened,
            )
    except AppError as error:
        raise Refusal("upload_refused") from error
    note_id = await _held_note(shelf, sha256)
    if note_id is None:
        raise RuntimeError("an accepted EHR document has no note")
    return ACCEPTED, note_id


async def _held_note(shelf: Shelf, sha256: str) -> str | None:
    return await shelf.db.scalar(
        select(Note.id).where(Note.practice_id == shelf.practice.id, Note.file_sha256 == sha256, Note.status != VOIDED)
    )


async def _record(
    shelf: Shelf,
    trail: Trail,
    outcome: str,
    *,
    reason: str | None = None,
    note_id: str | None = None,
    file: UploadFile | None = None,
) -> None:
    shelf.db.add(
        EhrDocument(
            practice_id=shelf.practice.id,
            run_id=shelf.run.id,
            document_id=trail.document.id,
            document_version=trail.document.version,
            encounter_id=trail.encounter_id,
            practitioner_id=trail.practitioner_id,
            outcome=outcome,
            reason=reason,
            note_id=note_id,
            file_sha256=hashlib.sha256(file.data).hexdigest() if file else None,
            file_bytes=len(file.data) if file else None,
        )
    )
    await shelf.db.commit()


def _charset(attachment: Attachment) -> str:
    for part in (attachment.contentType or "").split(";")[1:]:
        name, _, value = part.strip().partition("=")
        if name.lower() == "charset" and _known_codec(value.strip().strip('"')):
            return value.strip().strip('"')
    return DEFAULT_CHARSET


def _known_codec(name: str) -> bool:
    try:
        codecs.lookup(name)
    except LookupError:
        return False
    return bool(name)
