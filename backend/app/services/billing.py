from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import Select, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.codes.billing_codes import Code, claim_changes
from app.core.calendar import day_bounds, today_in
from app.models import AddendumRequest, ApprovedClaim, Note, Provider
from app.services.claim_holds import held_for_confirmation
from app.services.estimates import claim_amount
from app.services.worklists import count_of

__all__ = [
    "AUTO_APPROVER",
    "BILLING_SHOWS",
    "EXPORT_COLUMNS",
    "PAGE_SIZE",
    "ROW_LIMIT",
    "BillingFilter",
    "billing_csv",
    "billing_filter",
    "billing_rows",
    "billing_summary",
    "billing_total",
    "safe_cell",
]

ROW_LIMIT = 500
BILLING_SHOWS = ("ready", "exported", "today", "all")
READY, EXPORTED, TODAY, ALL = BILLING_SHOWS
AUTO_APPROVER = "Bodha (auto)"
PAGE_SIZE = 100
FORMULA_STARTS = ("=", "+", "-", "@", "\t", "\r")
EXPORT_COLUMNS = (
    "note_id",
    "patient",
    "service_date",
    "provider",
    "npi",
    "place_of_service",
    "cpt",
    "icd10",
    "approved_by",
    "approved_at",
)


@dataclass(frozen=True)
class BillingFilter:
    exported: bool | None = None
    exported_within: tuple[datetime, datetime] | None = None


def billing_filter(show: str, zone: ZoneInfo) -> BillingFilter:
    if show == TODAY:
        return BillingFilter(exported=True, exported_within=day_bounds(today_in(zone), zone))
    return BillingFilter(exported={READY: False, EXPORTED: True, ALL: None}[show])


async def billing_rows(
    db: AsyncSession, practice_id: str, wanted: BillingFilter, *, offset: int = 0, limit: int = ROW_LIMIT
) -> list[dict[str, Any]]:
    query = _billing_query(practice_id, wanted)
    rows = (await db.execute(query.offset(offset).limit(limit))).all()
    held = await held_for_confirmation(db, [note.id for note, _, _ in rows])
    return [_row(note, provider, snapshot, held=note.id in held) for note, provider, snapshot in rows]


async def billing_total(db: AsyncSession, practice_id: str, wanted: BillingFilter) -> int:
    return await count_of(db, _billing_query(practice_id, wanted).with_only_columns(Note.id))


def _billing_query(practice_id: str, wanted: BillingFilter) -> Select[Any]:
    latest = (
        select(ApprovedClaim.note_id, func.max(ApprovedClaim.revision).label("revision"))
        .group_by(ApprovedClaim.note_id)
        .subquery()
    )
    query = (
        select(Note, Provider, ApprovedClaim)
        .join(Provider, Provider.id == Note.provider_id)
        .join(latest, latest.c.note_id == Note.id)
        .join(ApprovedClaim, and_(ApprovedClaim.note_id == Note.id, ApprovedClaim.revision == latest.c.revision))
        .where(Note.practice_id == practice_id, Note.status.in_(("approved", "exported")))
        .order_by(Note.service_date.desc(), Note.approved_at.desc())
    )
    if wanted.exported is not None:
        query = query.where(Note.exported_at.is_not(None) if wanted.exported else Note.exported_at.is_(None))
    if wanted.exported_within is not None:
        start, end = wanted.exported_within
        query = query.where(Note.exported_at >= start, Note.exported_at < end)
    return query


async def billing_summary(db: AsyncSession, practice_id: str, zone: ZoneInfo) -> dict[str, int]:
    held = select(func.count(func.distinct(AddendumRequest.note_id))).where(
        AddendumRequest.practice_id == practice_id,
        AddendumRequest.status == "sent",
        AddendumRequest.hold_claim.is_(True),
    )
    return {
        "ready": await billing_total(db, practice_id, billing_filter(READY, zone)),
        "exported_today": await billing_total(db, practice_id, billing_filter(TODAY, zone)),
        "held_for_provider": await db.scalar(held) or 0,
    }


def _row(note: Note, provider: Provider, snapshot: ApprovedClaim, *, held: bool) -> dict[str, Any]:
    final = [Code.from_json(item) for item in snapshot.content.get("codes", [])]
    billed = [Code.from_json(item) for item in snapshot.content.get("billed", [])]
    return {
        "id": note.id,
        "patient_name": note.patient_name,
        "service_date": note.service_date.isoformat(),
        "provider_name": provider.name,
        "npi": provider.npi,
        "place_code": note.place_code,
        "codes": [code.label() for code in final],
        "changed": claim_changes(final, billed),
        "estimate": claim_amount(final, note.place_code, note.service_date),
        "approved_by": snapshot.approver_name or AUTO_APPROVER,
        "approved_at": note.approved_at.isoformat() if note.approved_at else None,
        "exported_at": note.exported_at.isoformat() if note.exported_at else None,
        "cpt": [code.as_text() for code in final if code.type == "CPT"],
        "icd10": [code.code for code in final if code.type == "ICD-10"],
        "snapshot_id": snapshot.id,
        "snapshot_revision": snapshot.revision,
        "held": held,
    }


def billing_csv(rows: list[dict[str, Any]]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(EXPORT_COLUMNS)
    for row in rows:
        values = [
            row["id"],
            row["patient_name"],
            row["service_date"],
            row["provider_name"],
            row["npi"],
            row["place_code"],
            " ".join(row["cpt"]),
            " ".join(row["icd10"]),
            row["approved_by"],
            row["approved_at"],
        ]
        writer.writerow([safe_cell(value) for value in values])
    return buffer.getvalue()


def safe_cell(value: object) -> str:
    text = "" if value is None else str(value)
    return f"'{text}" if text[:1] in FORMULA_STARTS else text
