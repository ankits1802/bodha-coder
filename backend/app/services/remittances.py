from __future__ import annotations

import hashlib
from collections import Counter
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.object_store import ObjectStore, practice_prefix
from app.core.config import get_settings
from app.core.deps import Actor
from app.core.errors import Conflict, Invalid
from app.models import Practice, Remittance, RemittanceLine, new_id
from app.services.audit_log import record_access
from app.services.payers import payer_list
from app.services.remittance_835 import ClaimPayment, PaymentAdvice, ServicePayment, parse_835
from app.services.remittance_matching import matching_note
from app.services.remittance_outcomes import APPEALABLE, UNMATCHED, line_outcome, plan_type_for

__all__ = ["APPEAL_DAYS_KEY", "UploadedRemittance", "listed_plan_type", "remittance_key", "upload_remittance"]

APPEAL_DAYS_KEY = "appeal_days"
CONTENT_TYPE = "application/edi-x12"
DAY_FORMAT = "%d %b %Y"


@dataclass(frozen=True)
class UploadedRemittance:
    ids: list[str]
    counts: dict[str, int]


def remittance_key(practice_id: str, remittance_id: str) -> str:
    return f"{practice_prefix(practice_id)}remittances/{remittance_id}.835"


async def upload_remittance(
    db: AsyncSession, store: ObjectStore, actor: Actor, file_name: str, data: bytes
) -> UploadedRemittance:
    limit = get_settings().max_upload_mb
    if not data:
        raise Invalid(f"{file_name} is empty")
    if len(data) > limit * 1024 * 1024:
        raise Invalid(f"{file_name} is larger than {limit} MB")
    advices = parse_835(data)
    name = file_name.strip()[:255] or "remittance.835"
    checksum = hashlib.sha256(data).hexdigest()
    await _refuse_duplicate(db, store, actor, checksum)
    practice = await db.get_one(Practice, actor.practice_id)
    first_id = new_id()
    key = remittance_key(actor.practice_id, first_id)
    await store.put(key, data, content_type=CONTENT_TYPE)
    counts: Counter[str] = Counter()
    ids: list[str] = []
    for index, advice in enumerate(advices):
        remittance = Remittance(
            id=first_id if index == 0 else new_id(),
            practice_id=actor.practice_id,
            file_key=key,
            file_name=name,
            payer=(advice.payer_name or "")[:120] or None,
            paid_on=advice.paid_on,
            uploaded_by=actor.user.id,
            file_sha256=checksum,
        )
        db.add(remittance)
        await db.flush()
        counts.update(await _add_lines(db, practice, remittance, advice))
        ids.append(remittance.id)
    record_access(db, actor, "uploaded remittance", detail=f"{counts.total()} lines, remittance {first_id}")
    await db.commit()
    return UploadedRemittance(ids, dict(counts))


async def _refuse_duplicate(db: AsyncSession, store: ObjectStore, actor: Actor, checksum: str) -> None:
    await _record_missing_checksums(db, store, actor.practice_id)
    await db.execute(select(func.pg_advisory_xact_lock(func.hashtextextended(f"remittance:{actor.practice_id}", 0))))
    earlier = (
        await db.execute(
            select(Remittance.created_at, Remittance.file_name)
            .where(Remittance.practice_id == actor.practice_id, Remittance.file_sha256 == checksum)
            .order_by(Remittance.created_at)
            .limit(1)
        )
    ).first()
    if earlier is not None:
        day = earlier.created_at.astimezone(actor.zone).date()
        raise Conflict(f"this file was already uploaded on {day.strftime(DAY_FORMAT)} as {earlier.file_name}")


async def _record_missing_checksums(db: AsyncSession, store: ObjectStore, practice_id: str) -> None:
    mine = Remittance.practice_id == practice_id
    missing = select(Remittance.file_key).where(mine, Remittance.file_sha256.is_(None)).distinct()
    keys = (await db.scalars(missing)).all()
    for key in keys:
        checksum = hashlib.sha256(await store.get(key)).hexdigest()
        await db.execute(update(Remittance).where(mine, Remittance.file_key == key).values(file_sha256=checksum))
    if keys:
        await db.commit()


async def _add_lines(
    db: AsyncSession, practice: Practice, remittance: Remittance, advice: PaymentAdvice
) -> Counter[str]:
    listed = listed_plan_type(payer_list(practice), advice.payer_id, advice.payer_name)
    counts: Counter[str] = Counter()
    for claim in advice.claims:
        plan_type = plan_type_for(claim.filing_indicator, listed)
        for line in claim.payments():
            outcome = line_outcome(line, claim.status)
            note_id = await matching_note(db, practice.id, claim, line)
            row = _line_row(remittance.id, claim, line, note_id=note_id, outcome=outcome)
            row.appeal_plan_type = plan_type if outcome in APPEALABLE else None
            db.add(row)
            counts[row.status] += 1
    return counts


def _line_row(
    remittance_id: str, claim: ClaimPayment, line: ServicePayment, *, note_id: str | None, outcome: str
) -> RemittanceLine:
    return RemittanceLine(
        remittance_id=remittance_id,
        note_id=note_id,
        claim_ref=claim.claim_ref[:80],
        patient_name=claim.patient_name,
        service_date=line.service_date or claim.service_date,
        billed_code=line.billed_code,
        paid_code=line.paid_code,
        billed_amount=line.billed_cents,
        paid_amount=line.paid_cents,
        adjustments=[item.as_json() for item in line.adjustments],
        status=outcome if note_id else UNMATCHED,
    )


def listed_plan_type(payers: list[dict[str, Any]], payer_id: str | None, payer_name: str | None) -> str | None:
    wanted_id = (payer_id or "").strip().upper()
    wanted_name = (payer_name or "").strip().lower()
    for payer in payers:
        if wanted_id and (payer.get("payer_id") or "") == wanted_id:
            return payer["plan_type"]
        if wanted_name and payer["name"].lower() == wanted_name:
            return payer["plan_type"]
    return None
