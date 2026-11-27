from __future__ import annotations

import asyncio
import csv
import io
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.codes.billing_codes import MAX_MODIFIERS, MAX_POINTERS, Code
from app.codes.ncci import NcciTables, ncci_tables
from app.core.deps import Actor
from app.core.errors import Invalid
from app.models import Note, Provider
from app.services.audit_log import record_access
from app.services.billing import ROW_LIMIT, safe_cell
from app.services.code_sets import latest_codes
from app.services.placement import SETTLED_STATUSES
from app.services.review_actions import current_claim, note_for

__all__ = [
    "CLAIM_LINE_COLUMNS",
    "MAX_DIAGNOSES",
    "POINTER_LETTERS",
    "Claim",
    "ClaimLine",
    "ClaimParty",
    "add_on_primaries",
    "billing_npi",
    "build_claim",
    "claim_lines",
    "claims_csv",
    "claims_json",
    "line_pointers",
    "note_pointers",
    "pointers_view",
]

POINTER_LETTERS = "ABCDEFGHIJKL"
MAX_DIAGNOSES = len(POINTER_LETTERS)
INDIVIDUAL = "individual"
CLAIM_LINE_COLUMNS = (
    "note_id",
    "patient",
    "service_date",
    "place_of_service",
    "rendering_npi",
    "rendering_taxonomy",
    "billing_npi",
    "line",
    "procedure",
    *(f"modifier_{number}" for number in range(1, MAX_MODIFIERS + 1)),
    "units",
    "diagnosis_pointers",
    *(f"diagnosis_{letter.lower()}" for letter in POINTER_LETTERS),
)


@dataclass(frozen=True, slots=True)
class ClaimParty:
    note_id: str
    patient_name: str | None
    service_date: date
    place_code: str
    rendering_npi: str | None
    rendering_taxonomy: str | None
    billing_npi: str | None


@dataclass(frozen=True, slots=True)
class ClaimLine:
    number: int
    code: str
    modifiers: tuple[str, ...]
    units: int
    pointers: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Claim:
    party: ClaimParty
    diagnoses: tuple[str, ...]
    lines: tuple[ClaimLine, ...]


def billing_npi(npi: str | None, details: Mapping[str, Any]) -> str | None:
    if details.get("bills_under") == INDIVIDUAL:
        return npi
    return details.get("group_npi") or None


def line_pointers(codes: Sequence[Code], primaries: Mapping[str, str]) -> dict[str, tuple[str, ...]]:
    first = tuple(code.code for code in codes if code.type == "ICD-10")[:MAX_POINTERS]
    chosen = {code.code: code.pointers for code in codes if code.type == "CPT" and code.pointers}
    return {
        code.code: chosen.get(code.code) or chosen.get(primaries.get(code.code, ""), first)
        for code in codes
        if code.type == "CPT"
    }


def add_on_primaries(tables: NcciTables, codes: Sequence[Code], service_date: date) -> dict[str, str]:
    lines = [code.code for code in codes if code.type == "CPT"]
    found: dict[str, str] = {}
    for code in lines:
        rule = tables.add_on_primaries(code, service_date)
        primary = next((other for other in lines if rule is not None and other in rule.primaries), None)
        if primary is not None:
            found[code] = primary
    return found


def build_claim(party: ClaimParty, codes: tuple[Code, ...], *, primaries: Mapping[str, str] | None = None) -> Claim:
    diagnoses = tuple(code.code for code in codes if code.type == "ICD-10")
    if not diagnoses:
        raise Invalid(f"note {party.note_id} has no diagnosis code to bill")
    if len(diagnoses) > MAX_DIAGNOSES:
        raise Invalid(f"note {party.note_id} has {len(diagnoses)} diagnosis codes; a claim carries at most 12")
    procedures = [code for code in codes if code.type == "CPT"]
    if not procedures:
        raise Invalid(f"note {party.note_id} has no procedure code to bill")
    letters = dict(zip(diagnoses, POINTER_LETTERS, strict=False))
    pointed = line_pointers(codes, primaries or {})
    lines = tuple(
        _line(number, code, _letters(party, code, pointed[code.code], letters))
        for number, code in enumerate(procedures, start=1)
    )
    return Claim(party, tuple(code.replace(".", "") for code in diagnoses), lines)


async def note_pointers(db: AsyncSession, actor: Actor, note_id: str) -> dict[str, Any]:
    note = await note_for(db, actor, note_id)
    settled = note.status in SETTLED_STATUSES
    codes = await latest_codes(db, note.id, "final") if settled else await current_claim(db, note)
    tables = await asyncio.to_thread(ncci_tables)
    record_access(db, actor, "opened diagnosis pointers", note_id=note.id)
    await db.commit()
    return pointers_view(codes, add_on_primaries(tables, codes, note.service_date))


def pointers_view(codes: Sequence[Code], primaries: Mapping[str, str]) -> dict[str, Any]:
    pointed = line_pointers(codes, primaries)
    diagnoses = [code.code for code in codes if code.type == "ICD-10"]
    return {
        "diagnoses": [
            {"code": code, "letter": POINTER_LETTERS[index] if index < MAX_DIAGNOSES else None}
            for index, code in enumerate(diagnoses)
        ],
        "lines": [
            {
                "code": code.code,
                "label": code.label(),
                "pointers": list(pointed[code.code]),
                "stored": bool(code.pointers),
            }
            for code in codes
            if code.type == "CPT"
        ],
    }


async def claim_lines(db: AsyncSession, actor: Actor, note_ids: list[str] | None) -> list[Claim]:
    query = (
        select(Note, Provider)
        .join(Provider, Provider.id == Note.provider_id)
        .where(Note.practice_id == actor.practice_id, Note.status == "approved", Note.exported_at.is_(None))
        .order_by(Note.service_date, Note.approved_at)
        .limit(ROW_LIMIT)
    )
    if note_ids is not None:
        query = query.where(Note.id.in_(note_ids))
    rows = (await db.execute(query)).all()
    if not rows:
        raise Invalid("no approved visits are waiting for export")
    tables = await asyncio.to_thread(ncci_tables)
    claims = [await _final_claim(db, tables, note, provider) for note, provider in rows]
    record_access(db, actor, "built claim lines", detail=f"{len(claims)} visits")
    await db.commit()
    return claims


def claims_json(claims: list[Claim]) -> dict[str, Any]:
    return {"claims": [_claim_json(claim) for claim in claims]}


def claims_csv(claims: list[Claim]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(CLAIM_LINE_COLUMNS)
    for claim in claims:
        party = claim.party
        shared = [
            party.note_id,
            party.patient_name,
            party.service_date.isoformat(),
            party.place_code,
            party.rendering_npi,
            party.rendering_taxonomy,
            party.billing_npi,
        ]
        diagnoses = [*claim.diagnoses, *([""] * (MAX_DIAGNOSES - len(claim.diagnoses)))]
        for line in claim.lines:
            modifiers = [*line.modifiers, *([""] * (MAX_MODIFIERS - len(line.modifiers)))]
            values = [*shared, line.number, line.code, *modifiers, line.units, "".join(line.pointers), *diagnoses]
            writer.writerow([safe_cell(value) for value in values])
    return buffer.getvalue()


async def _final_claim(db: AsyncSession, tables: NcciTables, note: Note, provider: Provider) -> Claim:
    codes = await latest_codes(db, note.id, "final")
    return build_claim(_party(note, provider), codes, primaries=add_on_primaries(tables, codes, note.service_date))


def _letters(party: ClaimParty, code: Code, pointers: tuple[str, ...], letters: Mapping[str, str]) -> tuple[str, ...]:
    unknown = [pointer for pointer in pointers if pointer not in letters]
    if unknown:
        raise Invalid(f"{code.label()} on note {party.note_id} points to {', '.join(unknown)}, which the claim lacks")
    return tuple(letters[pointer] for pointer in pointers)


def _line(number: int, code: Code, pointers: tuple[str, ...]) -> ClaimLine:
    if len(code.modifiers) > MAX_MODIFIERS:
        raise Invalid(f"{code.label()} has more than {MAX_MODIFIERS} modifiers")
    return ClaimLine(number, code.code, code.modifiers, code.units, pointers)


def _party(note: Note, provider: Provider) -> ClaimParty:
    details = provider.details or {}
    return ClaimParty(
        note.id,
        note.patient_name,
        note.service_date,
        note.place_code,
        provider.npi,
        details.get("taxonomy_code"),
        billing_npi(provider.npi, details),
    )


def _claim_json(claim: Claim) -> dict[str, Any]:
    party = claim.party
    return {
        "note_id": party.note_id,
        "patient_name": party.patient_name,
        "service_date": party.service_date.isoformat(),
        "place_of_service": party.place_code,
        "rendering_npi": party.rendering_npi,
        "rendering_taxonomy": party.rendering_taxonomy,
        "billing_npi": party.billing_npi,
        "diagnoses": [
            {"pointer": letter, "code": code} for letter, code in zip(POINTER_LETTERS, claim.diagnoses, strict=False)
        ],
        "lines": [
            {
                "line": line.number,
                "procedure": line.code,
                "modifiers": list(line.modifiers),
                "units": line.units,
                "pointers": list(line.pointers),
            }
            for line in claim.lines
        ],
    }
