from __future__ import annotations

import csv
import io
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import Select, and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.codes.billing_codes import Code, claim_changes
from app.core.calendar import day_bounds, today_in
from app.core.deps import Actor
from app.core.errors import Invalid
from app.models import AddendumRequest, CodeSet, Note, Provider, User, utcnow
from app.services.audit_log import record_access
from app.services.estimates import claim_amount
from app.services.worklists import count_of

ROW_LIMIT = 500
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


def _latest(kind: str) -> Any:
    latest = (
        select(CodeSet.note_id, func.max(CodeSet.revision).label("revision"))
        .where(CodeSet.kind == kind)
        .group_by(CodeSet.note_id)
    )
    return latest.subquery()


async def billing_rows(
    db: AsyncSession, practice_id: str, *, exported: bool | None, offset: int = 0, limit: int = ROW_LIMIT
) -> list[dict[str, Any]]:
    query = _billing_query(practice_id, exported=exported)
    rows = (await db.execute(query.offset(offset).limit(limit))).all()
    return [
        _row(note, provider, approver, final_codes, billed_codes)
        for note, provider, approver, final_codes, billed_codes in rows
    ]


async def billing_total(db: AsyncSession, practice_id: str, *, exported: bool | None) -> int:
    return await count_of(db, _billing_query(practice_id, exported=exported).with_only_columns(Note.id))


def _billing_query(practice_id: str, *, exported: bool | None) -> Select[Any]:
    final, billed = _latest("final"), _latest("billed")
    final_set, billed_set = CodeSet.__table__.alias("final_set"), CodeSet.__table__.alias("billed_set")
    query = (
        select(Note, Provider, User.name, final_set.c.codes, billed_set.c.codes)
        .join(Provider, Provider.id == Note.provider_id)
        .join(User, User.id == Note.approved_by)
        .join(final, final.c.note_id == Note.id)
        .join(
            final_set,
            and_(final_set.c.note_id == Note.id, final_set.c.revision == final.c.revision, final_set.c.kind == "final"),
        )
        .join(billed, billed.c.note_id == Note.id)
        .join(
            billed_set,
            and_(
                billed_set.c.note_id == Note.id,
                billed_set.c.revision == billed.c.revision,
                billed_set.c.kind == "billed",
            ),
        )
        .where(Note.practice_id == practice_id, Note.status.in_(("approved", "exported")))
        .order_by(Note.service_date.desc(), Note.approved_at.desc())
    )
    if exported is not None:
        query = query.where(Note.exported_at.is_not(None) if exported else Note.exported_at.is_(None))
    return query


async def billing_summary(db: AsyncSession, practice_id: str, zone: ZoneInfo) -> dict[str, int]:
    start, end = day_bounds(today_in(zone), zone)
    mine = Note.practice_id == practice_id
    ready = select(func.count()).select_from(Note).where(mine, Note.status == "approved", Note.exported_at.is_(None))
    exported = select(func.count()).select_from(Note).where(mine, Note.exported_at >= start, Note.exported_at < end)
    held = select(func.count(func.distinct(AddendumRequest.note_id))).where(
        AddendumRequest.practice_id == practice_id,
        AddendumRequest.status == "sent",
        AddendumRequest.hold_claim.is_(True),
    )
    return {
        "ready": await db.scalar(ready) or 0,
        "exported_today": await db.scalar(exported) or 0,
        "held_for_provider": await db.scalar(held) or 0,
    }


def _row(
    note: Note, provider: Provider, approver: str, final_codes: list[dict[str, Any]], billed_codes: list[dict[str, Any]]
) -> dict[str, Any]:
    final = [Code.from_json(item) for item in final_codes]
    billed = [Code.from_json(item) for item in billed_codes]
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
        "approved_by": approver,
        "approved_at": note.approved_at.isoformat() if note.approved_at else None,
        "exported_at": note.exported_at.isoformat() if note.exported_at else None,
        "cpt": [code.as_text() for code in final if code.type == "CPT"],
        "icd10": [code.code for code in final if code.type == "ICD-10"],
    }


async def export_csv(db: AsyncSession, actor: Actor, note_ids: list[str] | None, *, again: bool = False) -> str:
    if again and not note_ids:
        raise Invalid("choose the visits to download again")
    rows = await billing_rows(db, actor.practice_id, exported=again)
    chosen = [row for row in rows if note_ids is None or row["id"] in note_ids]
    if not chosen:
        raise Invalid("nothing to export")
    if not again:
        stamp = utcnow()
        for note in (await db.scalars(select(Note).where(Note.id.in_([row["id"] for row in chosen])))).all():
            note.status, note.exported_at = "exported", stamp
    action = "downloaded an export again" if again else "exported claims"
    record_access(db, actor, action, detail=f"{len(chosen)} visits")
    await db.commit()
    return _csv(chosen)


def _csv(rows: list[dict[str, Any]]) -> str:
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
