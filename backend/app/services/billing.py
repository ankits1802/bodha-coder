from __future__ import annotations

import csv
import io
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.calendar import day_bounds, today_in
from app.core.deps import Actor
from app.core.errors import Invalid
from app.models import AddendumRequest, CodeSet, Note, Provider, User, utcnow
from app.services.audit_log import record_access

ROW_LIMIT = 500
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


async def billing_rows(db: AsyncSession, practice_id: str, *, exported: bool | None) -> list[dict[str, Any]]:
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
    rows = (await db.execute(query.limit(ROW_LIMIT))).all()
    return [
        _row(note, provider, approver, final_codes, billed_codes)
        for note, provider, approver, final_codes, billed_codes in rows
    ]


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
    labels = ["-".join([item["code"], *item.get("modifiers", [])]) for item in final_codes]
    changed = len({item["code"] for item in final_codes} ^ {item["code"] for item in billed_codes})
    return {
        "id": note.id,
        "patient_name": note.patient_name,
        "service_date": note.service_date.isoformat(),
        "provider_name": provider.name,
        "npi": provider.npi,
        "place_code": note.place_code,
        "codes": labels,
        "changed": changed,
        "approved_by": approver,
        "approved_at": note.approved_at.isoformat() if note.approved_at else None,
        "exported_at": note.exported_at.isoformat() if note.exported_at else None,
        "cpt": [label for label, item in zip(labels, final_codes, strict=True) if item["type"] == "CPT"],
        "icd10": [item["code"] for item in final_codes if item["type"] == "ICD-10"],
    }


async def export_csv(db: AsyncSession, actor: Actor, note_ids: list[str] | None) -> str:
    rows = await billing_rows(db, actor.practice_id, exported=False)
    chosen = [row for row in rows if note_ids is None or row["id"] in note_ids]
    if not chosen:
        raise Invalid("nothing to export")
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(EXPORT_COLUMNS)
    for row in chosen:
        writer.writerow(
            [
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
        )
    stamp = utcnow()
    for note in (await db.scalars(select(Note).where(Note.id.in_([row["id"] for row in chosen])))).all():
        note.status, note.exported_at = "exported", stamp
    record_access(db, actor, "exported claims", detail=f"{len(chosen)} visits")
    await db.commit()
    return buffer.getvalue()
