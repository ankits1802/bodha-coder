from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.object_store import ObjectStore
from app.core.calendar import today_in, zone_named
from app.core.deps import Actor
from app.core.errors import Conflict, NotFound
from app.models import Note, Practice, Provider, Remittance, RemittanceLine, User
from app.services.appeal_letters import AppealFacts, appeal_letter
from app.services.audit_log import record_access, record_activity
from app.services.payers import payer_list
from app.services.remittance_835 import Adjustment, ClaimPayment, ServicePayment, parse_835
from app.services.remittance_outcomes import (
    APPEALABLE,
    DENIED,
    appeal_days,
    line_appeal_by,
    line_outcome,
    plan_type_for,
    validated_appeal_days,
)
from app.services.remittances import APPEAL_DAYS_KEY, listed_plan_type

__all__ = [
    "PAGE_SIZE",
    "appeal_draft",
    "defense_packet_path",
    "remittance_detail",
    "remittance_page",
    "save_appeal_days",
    "stored_appeal_days",
]

PAGE_SIZE = 50
LINE_LIMIT = 2000


def defense_packet_path(note_id: str) -> str:
    return f"/api/notes/{note_id}/defense-packet"


async def remittance_page(db: AsyncSession, actor: Actor, *, offset: int) -> dict[str, Any]:
    mine = Remittance.practice_id == actor.practice_id
    rows = (
        await db.execute(
            select(Remittance, User.name)
            .join(User, User.id == Remittance.uploaded_by)
            .where(mine)
            .order_by(Remittance.created_at.desc(), Remittance.id)
            .offset(offset)
            .limit(PAGE_SIZE)
        )
    ).all()
    days = await stored_appeal_days(db, actor)
    counts, next_appeal = await _line_summaries(db, [remittance for remittance, _ in rows], days)
    return {
        "items": [
            {
                **_remittance_view(remittance, uploader),
                "counts": counts.get(remittance.id, {}),
                "next_appeal_by": next_appeal.get(remittance.id),
            }
            for remittance, uploader in rows
        ],
        "total": await db.scalar(select(func.count()).select_from(Remittance).where(mine)) or 0,
        "offset": offset,
        "page_size": PAGE_SIZE,
    }


async def _line_summaries(
    db: AsyncSession, remittances: Sequence[Remittance], days: Mapping[str, int]
) -> tuple[dict[str, dict[str, int]], dict[str, str]]:
    paid_on = {remittance.id: remittance.paid_on for remittance in remittances}
    if not paid_on:
        return {}, {}
    grouping = (RemittanceLine.remittance_id, RemittanceLine.status, RemittanceLine.appeal_plan_type)
    rows = await db.execute(
        select(*grouping, func.count(), func.min(RemittanceLine.appeal_by))
        .where(RemittanceLine.remittance_id.in_(list(paid_on)))
        .group_by(*grouping)
    )
    counts: dict[str, Counter[str]] = {}
    soonest: dict[str, date] = {}
    for remittance_id, status, plan_type, count, stored in rows.all():
        counts.setdefault(remittance_id, Counter())[status] += count
        due = line_appeal_by(paid_on[remittance_id], plan_type, stored, days)
        if due is not None and (remittance_id not in soonest or due < soonest[remittance_id]):
            soonest[remittance_id] = due
    return {key: dict(value) for key, value in counts.items()}, {key: due.isoformat() for key, due in soonest.items()}


async def remittance_detail(
    db: AsyncSession, actor: Actor, remittance_id: str, *, status: str | None
) -> dict[str, Any]:
    remittance = await db.get(Remittance, remittance_id)
    if remittance is None or remittance.practice_id != actor.practice_id:
        raise NotFound("remittance not found")
    uploader = await db.scalar(select(User.name).where(User.id == remittance.uploaded_by))
    query = select(RemittanceLine).where(RemittanceLine.remittance_id == remittance.id)
    if status is not None:
        query = query.where(RemittanceLine.status == status)
    lines = (
        await db.scalars(
            query.order_by(RemittanceLine.service_date, RemittanceLine.claim_ref, RemittanceLine.id).limit(LINE_LIMIT)
        )
    ).all()
    days = await stored_appeal_days(db, actor)
    counts, _ = await _line_summaries(db, [remittance], days)
    record_access(db, actor, "viewed remittance", detail=f"remittance {remittance.id}, {len(lines)} lines")
    await db.commit()
    return {
        "remittance": {**_remittance_view(remittance, uploader or ""), "counts": counts.get(remittance.id, {})},
        "lines": [_line_view(line, _appeal_by(remittance, line, days)) for line in lines],
    }


def _remittance_view(remittance: Remittance, uploader: str) -> dict[str, Any]:
    return {
        "id": remittance.id,
        "file_name": remittance.file_name,
        "payer": remittance.payer,
        "paid_on": remittance.paid_on.isoformat() if remittance.paid_on else None,
        "uploaded_by": uploader,
        "uploaded_at": remittance.created_at.isoformat(),
    }


def _appeal_by(remittance: Remittance, line: RemittanceLine, days: Mapping[str, int]) -> date | None:
    return line_appeal_by(remittance.paid_on, line.appeal_plan_type, line.appeal_by, days)


def _line_view(line: RemittanceLine, appeal_by: date | None) -> dict[str, Any]:
    return {
        "id": line.id,
        "note_id": line.note_id,
        "claim_ref": line.claim_ref,
        "patient_name": line.patient_name,
        "service_date": line.service_date.isoformat() if line.service_date else None,
        "billed_code": line.billed_code,
        "paid_code": line.paid_code,
        "billed_amount": line.billed_amount,
        "paid_amount": line.paid_amount,
        "adjustments": line.adjustments,
        "status": line.status,
        "appeal_by": appeal_by.isoformat() if appeal_by else None,
    }


async def appeal_draft(db: AsyncSession, store: ObjectStore, actor: Actor, line_id: str) -> dict[str, Any]:
    line = await db.get(RemittanceLine, line_id)
    remittance = await db.get(Remittance, line.remittance_id) if line else None
    if line is None or remittance is None or remittance.practice_id != actor.practice_id:
        raise NotFound("remittance line not found")
    appeal_by = _appeal_by(remittance, line, await stored_appeal_days(db, actor))
    if appeal_by is None:
        raise Conflict("only a denied or downcoded line has an appeal")
    practice = await db.get_one(Practice, actor.practice_id)
    claim = await _claim_in_file(store, remittance, line)
    facts = await _appeal_facts(db, practice, remittance, line, claim)
    record_access(db, actor, "drafted appeal", note_id=line.note_id, detail=f"remittance line {line.id}")
    await db.commit()
    return {
        "line_id": line.id,
        "note_id": line.note_id,
        "appeal_by": appeal_by.isoformat(),
        "text": appeal_letter(facts),
        "file_name": f"appeal-{line.id}.txt",
        "defense_packet": defense_packet_path(line.note_id) if line.note_id else None,
    }


async def _claim_in_file(store: ObjectStore, remittance: Remittance, line: RemittanceLine) -> ClaimPayment | None:
    advices = parse_835(await store.get(remittance.file_key))
    for advice in advices:
        if advice.paid_on != remittance.paid_on:
            continue
        found = next((claim for claim in advice.claims if claim.claim_ref[:80] == line.claim_ref), None)
        if found is not None:
            return found
    return None


async def _appeal_facts(
    db: AsyncSession, practice: Practice, remittance: Remittance, line: RemittanceLine, claim: ClaimPayment | None
) -> AppealFacts:
    adjustments = tuple(Adjustment.from_json(item) for item in line.adjustments)
    payment = ServicePayment(
        line.billed_code, line.paid_code, line.billed_amount or 0, line.paid_amount or 0, line.service_date, adjustments
    )
    listed = listed_plan_type(payer_list(practice), None, remittance.payer)
    outcome = line_outcome(payment, claim.status if claim else "")
    return AppealFacts(
        practice_name=str((practice.setup.get("practice_details") or {}).get("legal_name") or practice.name),
        payer_name=remittance.payer,
        plan_type=line.appeal_plan_type or plan_type_for(claim.filing_indicator if claim else None, listed),
        outcome=outcome if outcome in APPEALABLE else DENIED,
        patient_name=line.patient_name,
        member_id=claim.member_id if claim else None,
        payer_claim_number=claim.payer_claim_number if claim else None,
        claim_ref=line.claim_ref,
        service_date=line.service_date,
        provider=await _provider_label(db, line.note_id),
        billed_code=line.billed_code,
        paid_code=line.paid_code,
        billed_cents=line.billed_amount,
        paid_cents=line.paid_amount,
        adjustments=adjustments,
        written_on=today_in(zone_named(practice.time_zone)),
    )


async def _provider_label(db: AsyncSession, note_id: str | None) -> str | None:
    note = await db.get(Note, note_id) if note_id else None
    provider = await db.get(Provider, note.provider_id) if note else None
    if provider is None:
        return None
    label = f"{provider.name}, {provider.credential}"
    return f"{label}, NPI {provider.npi}" if provider.npi else label


async def stored_appeal_days(db: AsyncSession, actor: Actor) -> dict[str, int]:
    practice = await db.get_one(Practice, actor.practice_id)
    return appeal_days(practice.setup.get(APPEAL_DAYS_KEY))


async def save_appeal_days(db: AsyncSession, actor: Actor, values: dict[str, int]) -> dict[str, int]:
    chosen = validated_appeal_days(values)
    practice = await db.get_one(Practice, actor.practice_id, with_for_update=True, populate_existing=True)
    merged = {**appeal_days(practice.setup.get(APPEAL_DAYS_KEY)), **chosen}
    practice.setup = {**practice.setup, APPEAL_DAYS_KEY: merged}
    detail = ", ".join(f"{key} {value}" for key, value in sorted(merged.items()))
    record_activity(db, actor, "appeal windows saved", practice_id=practice.id, detail=detail)
    await db.commit()
    return merged
