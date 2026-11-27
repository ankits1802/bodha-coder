from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import VOIDED, AddendumRequest, Decision, Note, Suggestion
from app.services.auto_approval import auto_approve, auto_approve_eligible
from app.services.code_sets import latest_codes
from app.services.estimates import impact_cents
from app.services.findings import Finding
from app.services.routing import choices_for, claim, has_diagnosis_codes, place

SETTLED_STATUSES = ("approved", "exported")
FROZEN_STATUSES = (*SETTLED_STATUSES, VOIDED)


def finding_from(row: Suggestion) -> Finding:
    detail = dict(row.detail)
    default_choice = detail.pop("default_choice", "accept")
    return Finding(
        kind=row.kind,
        key=row.key,
        action=row.action,
        title=row.title,
        reasoning=row.reasoning,
        code_before=row.code_before,
        code_after=row.code_after,
        evidence=tuple(row.evidence),
        severity=row.severity,
        detail=detail,
        default_choice=default_choice,
    )


async def current_findings(db: AsyncSession, note: Note) -> list[Finding]:
    if note.current_analysis_id is None:
        return []
    rows = await db.scalars(select(Suggestion).where(Suggestion.analysis_id == note.current_analysis_id))
    return [finding_from(row) for row in rows]


async def current_decisions(db: AsyncSession, note_id: str) -> dict[str, str]:
    rows = await db.scalars(select(Decision).where(Decision.note_id == note_id).order_by(Decision.created_at))
    return {row.suggestion_key: row.choice for row in rows}


async def awaiting_provider(db: AsyncSession, note_id: str) -> bool:
    found = await db.scalar(
        select(AddendumRequest.id).where(AddendumRequest.note_id == note_id, AddendumRequest.status == "sent").limit(1)
    )
    return found is not None


async def refresh_placement(db: AsyncSession, note: Note) -> None:
    if note.status in FROZEN_STATUSES or note.current_analysis_id is None:
        return
    findings = await current_findings(db, note)
    billed = await latest_codes(db, note.id, "billed")
    placement = place(
        findings,
        flagged=note.flag_reason is not None,
        cleared=note.compliance_cleared_by is not None,
        awaiting_provider=await awaiting_provider(db, note.id),
        billed_diagnoses=has_diagnosis_codes(billed),
        returned=note.returned_at is not None,
    )
    note.lane, note.lane_reason, note.headline = placement.lane, placement.reason, placement.headline
    derived = claim(billed, findings, choices_for(findings, await current_decisions(db, note.id)))
    note.impact_cents = impact_cents(derived, billed, note.place_code, note.service_date)
    note.status = "ready"
    if await auto_approve_eligible(db, note):
        await auto_approve(db, note)
