from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.codes.credentials import LICENSE_STATES
from app.core.deps import Actor
from app.core.errors import Conflict, Invalid
from app.models import SELF_RELATIONSHIP, ClaimDetail, Note
from app.services.audit_log import record_access
from app.services.code_sets import next_revision
from app.services.remittance_matching import same_person
from app.services.review_actions import note_for

__all__ = [
    "BILLABLE_STATUSES",
    "DETAILS_OPENED",
    "DETAILS_SAVED",
    "DetailValues",
    "claim_details_view",
    "latest_details",
    "save_claim_details",
]

BILLABLE_STATUSES = ("approved", "exported")
DETAILS_OPENED = "opened claim details"
DETAILS_SAVED = "saved claim details"
EARLIEST_BIRTH = date(1900, 1, 1)
NAME = re.compile(r"^[A-Za-z][A-Za-z' .-]*$")
STREET = re.compile(r"^[A-Za-z0-9#&',./ -]+$")
CITY = re.compile(r"^[A-Za-z][A-Za-z' .-]*$")
MEMBER = re.compile(r"^[A-Za-z0-9-]{2,80}$")
GROUP = re.compile(r"^[A-Za-z0-9 -]{1,50}$")
ZIP = re.compile(r"^\d{5}(-?\d{4})?$")
SEXES = {"f": "F", "female": "F", "woman": "F", "m": "M", "male": "M", "man": "M"}


@dataclass(frozen=True)
class DetailValues:
    patient_last: str
    patient_first: str
    patient_birth_date: date
    patient_sex: str
    street: str
    street_2: str | None
    city: str
    state: str
    zip_code: str
    relationship: str
    member_id: str
    group_number: str | None
    subscriber_last: str | None
    subscriber_first: str | None


async def claim_details_view(db: AsyncSession, actor: Actor, note_id: str) -> dict[str, Any]:
    note = await _billable(db, actor, note_id)
    latest = (await latest_details(db, [note.id])).get(note.id)
    suggestion = None if latest else await _suggestion(db, note)
    record_access(db, actor, DETAILS_OPENED, note_id=note.id)
    await db.commit()
    return {"details": _view(latest) if latest else None, "suggested": suggestion}


async def save_claim_details(db: AsyncSession, actor: Actor, note_id: str, values: DetailValues) -> dict[str, Any]:
    note = await _billable(db, actor, note_id)
    await db.refresh(note, with_for_update=True)
    row = ClaimDetail(
        practice_id=note.practice_id,
        note_id=note.id,
        revision=await next_revision(db, ClaimDetail, note.id),
        **_validated(values, note),
        confirmed_by=actor.user.id,
        confirmer_name=actor.user.name,
        confirmer_role=actor.role,
    )
    db.add(row)
    record_access(db, actor, DETAILS_SAVED, note_id=note.id)
    await db.commit()
    return {"details": _view(row), "suggested": None}


async def latest_details(db: AsyncSession, note_ids: Sequence[str]) -> dict[str, ClaimDetail]:
    if not note_ids:
        return {}
    rows = await db.scalars(
        select(ClaimDetail)
        .where(ClaimDetail.note_id.in_(note_ids))
        .order_by(ClaimDetail.note_id, ClaimDetail.revision.desc())
        .distinct(ClaimDetail.note_id)
    )
    return {row.note_id: row for row in rows}


async def _billable(db: AsyncSession, actor: Actor, note_id: str) -> Note:
    note = await note_for(db, actor, note_id)
    if note.status not in BILLABLE_STATUSES:
        raise Conflict("claim details belong to approved visits")
    return note


def _validated(values: DetailValues, note: Note) -> dict[str, Any]:
    is_self = values.relationship == SELF_RELATIONSHIP
    if not EARLIEST_BIRTH <= values.patient_birth_date <= note.service_date:
        raise Invalid("the birth date must fall before the date of service")
    if not is_self and not (values.subscriber_last and values.subscriber_first):
        raise Invalid("name the subscriber when the patient is not the subscriber")
    clean = {
        "patient_last": _text(values.patient_last, NAME, "the patient's last name"),
        "patient_first": _text(values.patient_first, NAME, "the patient's first name"),
        "street": _text(values.street, STREET, "the street address"),
        "street_2": _text(values.street_2, STREET, "the second address line") if values.street_2 else None,
        "city": _text(values.city, CITY, "the city"),
        "zip_code": _text(values.zip_code, ZIP, "the ZIP code").replace("-", ""),
        "member_id": _text(values.member_id, MEMBER, "the member ID").upper(),
        "group_number": _text(values.group_number, GROUP, "the group number").upper() if values.group_number else None,
        "subscriber_last": None if is_self else _text(values.subscriber_last, NAME, "the subscriber's last name"),
        "subscriber_first": None if is_self else _text(values.subscriber_first, NAME, "the subscriber's first name"),
    }
    state = values.state.strip().upper()
    if state not in LICENSE_STATES:
        raise Invalid(f"{state or 'an empty state'} is not a US state or territory")
    fixed = {"patient_birth_date": values.patient_birth_date, "patient_sex": values.patient_sex, "state": state}
    return {**clean, **fixed, "relationship": values.relationship}


def _text(value: str | None, shape: re.Pattern[str], label: str) -> str:
    clean = " ".join((value or "").split())
    if not clean or shape.fullmatch(clean) is None:
        raise Invalid(f"{label} holds characters a claim cannot carry")
    return clean


async def _suggestion(db: AsyncSession, note: Note) -> dict[str, Any]:
    read = {
        "patient_name": note.patient_name,
        "patient_birth_date": note.patient_birth_date.isoformat() if note.patient_birth_date else None,
        "patient_sex": SEXES.get((note.patient_sex or "").strip().lower()),
    }
    earlier = await _earlier_details(db, note)
    if earlier is None:
        return {**read, "source": "note"}
    return {**_values(earlier), "patient_name": note.patient_name, "source": "earlier_claim"}


async def _earlier_details(db: AsyncSession, note: Note) -> ClaimDetail | None:
    if not note.patient_name or note.patient_birth_date is None:
        return None
    rows = await db.scalars(
        select(ClaimDetail)
        .join(Note, Note.id == ClaimDetail.note_id)
        .where(
            Note.practice_id == note.practice_id,
            ClaimDetail.note_id != note.id,
            ClaimDetail.patient_birth_date == note.patient_birth_date,
        )
        .order_by(ClaimDetail.created_at.desc())
        .limit(20)
    )
    name = note.patient_name
    return next((row for row in rows if same_person(f"{row.patient_first} {row.patient_last}", name)), None)


def _values(row: ClaimDetail) -> dict[str, Any]:
    fields = DetailValues.__dataclass_fields__
    found = {field: getattr(row, field) for field in fields}
    return {**found, "patient_birth_date": row.patient_birth_date.isoformat()}


def _view(row: ClaimDetail) -> dict[str, Any]:
    return {
        **_values(row),
        "revision": row.revision,
        "confirmed_at": row.created_at.isoformat(),
        "confirmed_by": row.confirmer_name,
    }
