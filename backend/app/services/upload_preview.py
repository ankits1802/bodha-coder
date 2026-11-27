from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.pdf_text import DocumentUnreadable, read_first_page_text
from app.codes.billing_codes import FilenameFacts, parse_note_filename
from app.core.calendar import today_in
from app.core.deps import Actor
from app.core.errors import Invalid
from app.models import Note, PlaceOfService, Provider
from app.services.audit_log import record_access
from app.services.upload_matching import FileMatch, ProviderRef, match_file
from app.services.uploads import check_pdf

__all__ = ["MAX_PREVIEW_FILES", "PreviewFile", "preview_files"]

MAX_PREVIEW_FILES = 100
PREVIEWED = "previewed uploads"


@dataclass(frozen=True)
class PreviewFile:
    name: str
    data: bytes

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.data).hexdigest()


async def preview_files(db: AsyncSession, actor: Actor, files: list[PreviewFile]) -> list[dict[str, Any]]:
    if not files:
        raise Invalid("add at least one PDF")
    if len(files) > MAX_PREVIEW_FILES:
        raise Invalid(f"add at most {MAX_PREVIEW_FILES} PDFs at a time")
    for file in files:
        check_pdf(file.name, file.data)
    providers = await _active_providers(db, actor.practice_id)
    places = dict(
        (await db.execute(select(PlaceOfService.code, PlaceOfService.name).where(PlaceOfService.active))).tuples().all()
    )
    held = await _held(db, actor.practice_id, [file.sha256 for file in files])
    today = today_in(actor.zone)
    previews = []
    for file in files:
        facts = parse_note_filename(file.name)
        text = await asyncio.to_thread(_first_page, file.data)
        match = match_file(text, facts, providers, places, today=today)
        previews.append(_view(file, facts, match, duplicate=file.sha256 in held))
    record_access(db, actor, PREVIEWED, detail=f"{len(files)} files")
    await db.commit()
    return previews


def _first_page(data: bytes) -> str:
    try:
        return read_first_page_text(data)
    except DocumentUnreadable:
        return ""


async def _active_providers(db: AsyncSession, practice_id: str) -> list[ProviderRef]:
    rows = await db.execute(
        select(Provider.id, Provider.name, Provider.npi, Provider.place_code)
        .where(Provider.practice_id == practice_id, Provider.active)
        .order_by(Provider.name, Provider.id)
    )
    return [ProviderRef(*row) for row in rows.tuples()]


async def _held(db: AsyncSession, practice_id: str, digests: list[str]) -> set[str]:
    rows = await db.scalars(
        select(Note.file_sha256).where(Note.practice_id == practice_id, Note.file_sha256.in_(digests))
    )
    return set(rows.all())


def _view(file: PreviewFile, facts: FilenameFacts, match: FileMatch, *, duplicate: bool) -> dict[str, Any]:
    return {
        "file_name": file.name,
        "cpt": facts.cpt,
        "duplicate": duplicate,
        "provider_id": match.provider.value,
        "service_date": match.service_date.value.isoformat() if match.service_date.value else None,
        "place_code": match.place.value,
        "patient_name": match.patient.value,
        "confidence": {
            "provider": match.provider.confidence,
            "service_date": match.service_date.confidence,
            "place": match.place.confidence,
            "patient": match.patient.confidence,
        },
        "overall": match.confidence,
        "check": match.needs_check,
    }
