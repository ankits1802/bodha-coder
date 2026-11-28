from __future__ import annotations

import asyncio
import hashlib
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.object_store import ObjectStore
from app.codes.billing_codes import parse_note_filename
from app.core.errors import AppError
from app.models import Note, Practice
from app.services.intake import ALREADY_UPLOADED, arrival_name
from app.services.intake_mail import Attachment
from app.services.intake_settings import IntakeConfig, intake_config
from app.services.payer_matching import PayerRef, confident_payer, payer_in, payer_refs
from app.services.upload_matching import CHECK_BELOW, FileMatch, ProviderRef, match_file
from app.services.upload_preview import active_places, active_providers, first_page_text
from app.services.uploads import PlannedBatch, UploadFile, UploadPlan, file_problem, stage_intake_upload

__all__ = [
    "ACCEPTED",
    "NO_PLACE",
    "NO_PROVIDER",
    "NO_SERVICE_DATE",
    "ONLY_PDF",
    "REFUSED",
    "FileOutcome",
    "deliver_attachments",
    "plan_for",
]

ACCEPTED = "accepted"
REFUSED = "refused"
ONLY_PDF = "only PDF files are read"
NO_PROVIDER = "page 1 does not name an active provider clearly enough"
NO_SERVICE_DATE = "page 1 does not show the date of service clearly enough"
NO_PLACE = "page 1 shows no place of service and intake has none set"
UNNAMED = "attachment.pdf"


@dataclass(frozen=True)
class FileOutcome:
    sha256: str
    size: int
    outcome: str
    reason: str | None = None
    note_id: str | None = None

    def as_json(self) -> dict[str, Any]:
        return {
            "sha256": self.sha256,
            "bytes": self.size,
            "outcome": self.outcome,
            "reason": self.reason,
            "note_id": self.note_id,
        }


@dataclass(frozen=True)
class PlacedFile:
    file: UploadFile
    plan: UploadPlan | None
    reason: str | None


@dataclass(frozen=True)
class Directory:
    providers: Sequence[ProviderRef]
    places: Mapping[str, str]
    config: IntakeConfig
    today: date
    payers: Sequence[PayerRef]


async def deliver_attachments(
    db: AsyncSession, store: ObjectStore, practice: Practice, attachments: Sequence[Attachment], *, today: date
) -> list[FileOutcome]:
    providers, places = await active_providers(db, practice.id), await active_places(db)
    directory = Directory(providers, places, intake_config(practice), today, payer_refs(practice))
    placed = [await _place(attachment, directory) for attachment in attachments]
    ready = [item for item in placed if item.plan is not None]
    if not ready:
        return [_outcome(item, None, {}) for item in placed]
    try:
        result = await stage_intake_upload(db, store, practice, _batches(ready))
    except AppError as error:
        return [_outcome(item, error.message if item.plan else None, {}) for item in placed]
    notes = await _note_ids(db, practice.id, result.batch_ids)
    unclaimed = Counter(result.accepted)
    outcomes: list[FileOutcome] = []
    for item in placed:
        accepted = item.plan is not None and unclaimed[item.file.name] > 0
        unclaimed[item.file.name] -= accepted
        outcomes.append(_outcome(item, None if accepted or item.plan is None else ALREADY_UPLOADED, notes))
    return outcomes


def plan_for(match: FileMatch, config: IntakeConfig) -> tuple[UploadPlan | None, str | None]:
    if match.provider.value is None or match.provider.confidence < CHECK_BELOW:
        return None, NO_PROVIDER
    if match.service_date.value is None or match.service_date.confidence < CHECK_BELOW:
        return None, NO_SERVICE_DATE
    place = match.place.value or config.place_code
    if not place:
        return None, NO_PLACE
    return UploadPlan(match.provider.value, match.service_date.value, place, config.visit_type), None


async def _place(attachment: Attachment, directory: Directory) -> PlacedFile:
    file = UploadFile(arrival_name(attachment.name or UNNAMED, attachment.data), attachment.data, None, None)
    if not attachment.is_pdf:
        return PlacedFile(file, None, ONLY_PDF)
    problem = file_problem(file)
    if problem is not None:
        return PlacedFile(file, None, problem)
    text = await asyncio.to_thread(first_page_text, file.data)
    facts = parse_note_filename(attachment.name)
    match = match_file(text, facts, directory.providers, directory.places, today=directory.today)
    plan, reason = plan_for(match, directory.config)
    payer = confident_payer(payer_in(text, directory.payers))
    return PlacedFile(replace(file, payer=payer), plan, reason)


def _batches(ready: Sequence[PlacedFile]) -> list[PlannedBatch]:
    grouped: dict[UploadPlan, list[UploadFile]] = {}
    for item in ready:
        if item.plan is not None:
            grouped.setdefault(item.plan, []).append(item.file)
    return list(grouped.items())


async def _note_ids(db: AsyncSession, practice_id: str, batch_ids: Sequence[str]) -> dict[str, str]:
    rows = await db.execute(
        select(Note.file_sha256, Note.id).where(Note.practice_id == practice_id, Note.batch_id.in_(batch_ids))
    )
    return dict(rows.tuples().all())


def _outcome(item: PlacedFile, refusal: str | None, notes: Mapping[str, str]) -> FileOutcome:
    sha256 = hashlib.sha256(item.file.data).hexdigest()
    reason = refusal or item.reason
    if reason is not None:
        return FileOutcome(sha256, len(item.file.data), REFUSED, reason)
    if sha256 not in notes:
        raise RuntimeError("an accepted intake attachment has no note in its batch")
    return FileOutcome(sha256, len(item.file.data), ACCEPTED, None, notes[sha256])
