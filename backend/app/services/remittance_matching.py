from __future__ import annotations

import re
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import VOIDED, CodeSet, Note
from app.services.remittance_835 import ClaimPayment, ServicePayment

__all__ = ["matching_note", "name_tokens", "same_person"]

NOTE_REFERENCE = re.compile(r"^[0-9a-f-]{8,36}$")
NAME_PARTS = re.compile(r"[^a-z]+")
MIN_NAME_TOKENS = 2


async def matching_note(db: AsyncSession, practice_id: str, claim: ClaimPayment, line: ServicePayment) -> str | None:
    day = line.service_date or claim.service_date
    by_reference = await _note_by_reference(db, practice_id, claim.claim_ref)
    if by_reference is not None:
        return by_reference.id if day is None or by_reference.service_date == day else None
    if day is None or not claim.patient_name or not line.billed_code:
        return None
    return await _note_by_visit(db, practice_id, claim.patient_name, day, line.billed_code)


async def _note_by_reference(db: AsyncSession, practice_id: str, claim_ref: str) -> Note | None:
    reference = claim_ref.strip().lower()
    if NOTE_REFERENCE.fullmatch(reference) is None:
        return None
    found = (
        await db.scalars(
            select(Note)
            .where(
                Note.practice_id == practice_id,
                Note.status != VOIDED,
                Note.id.startswith(reference, autoescape=True),
            )
            .limit(2)
        )
    ).all()
    return found[0] if len(found) == 1 else None


async def _note_by_visit(db: AsyncSession, practice_id: str, patient: str, day: date, code: str) -> str | None:
    notes = (
        await db.scalars(
            select(Note).where(
                Note.practice_id == practice_id,
                Note.status != VOIDED,
                Note.service_date == day,
                Note.patient_name.is_not(None),
            )
        )
    ).all()
    named = [note.id for note in notes if same_person(note.patient_name or "", patient)]
    if not named:
        return None
    codes = await _claim_codes(db, named)
    found = [note_id for note_id in named if code in codes.get(note_id, set())]
    return found[0] if len(found) == 1 else None


async def _claim_codes(db: AsyncSession, note_ids: list[str]) -> dict[str, set[str]]:
    rows = await db.execute(
        select(CodeSet.note_id, CodeSet.kind, CodeSet.codes)
        .where(CodeSet.note_id.in_(note_ids))
        .order_by(CodeSet.revision)
    )
    latest: dict[tuple[str, str], list[dict]] = {}
    for note_id, kind, codes in rows.all():
        latest[(note_id, kind)] = codes
    return {
        note_id: {
            str(item["code"])
            for item in latest.get((note_id, "final")) or latest.get((note_id, "billed")) or []
            if item.get("type") == "CPT"
        }
        for note_id in note_ids
    }


def name_tokens(name: str) -> frozenset[str]:
    return frozenset(part for part in NAME_PARTS.split(name.lower()) if len(part) > 1)


def same_person(first: str, second: str) -> bool:
    smaller, larger = sorted((name_tokens(first), name_tokens(second)), key=len)
    return len(smaller) >= MIN_NAME_TOKENS and smaller <= larger
