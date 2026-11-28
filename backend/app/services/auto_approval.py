from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.codes.billing_codes import format_code_list
from app.core.errors import Conflict
from app.core.security import digest
from app.models import CodeSet, Note, Provider, utcnow
from app.services import placement
from app.services.audit_log import SystemActor, record_system_access
from app.services.autonomy import provider_eligibility
from app.services.claim_snapshots import Approver, write_snapshot
from app.services.code_sets import latest_codes, next_revision
from app.services.finding import SEVERE_AUDIT
from app.services.routing import choices_for, claim, open_questions

__all__ = [
    "AUTO_ACTOR_ID",
    "AUTO_ACTOR_NAME",
    "AUTO_REASON",
    "QUALITY_CHECK_EVERY",
    "auto_approve",
    "auto_approve_eligible",
    "held_for_quality_check",
]

QUALITY_CHECK_EVERY = 10
HASH_PREFIX = 8
AUTO_REASON = "auto"
AUTO_ACTOR_ID = "bodha-auto"
AUTO_ACTOR_NAME = "Bodha (auto)"
AUTO_ACTOR = SystemActor(AUTO_ACTOR_ID, AUTO_ACTOR_NAME)
AUTO_APPROVER = Approver(None, AUTO_ACTOR_NAME, "system")
MATCHES = "matches"


def held_for_quality_check(note_id: str) -> bool:
    return int(digest(note_id)[:HASH_PREFIX], 16) % QUALITY_CHECK_EVERY == 0


async def auto_approve_eligible(db: AsyncSession, note: Note) -> bool:
    if not _waiting_as_a_match(note) or held_for_quality_check(note.id):
        return False
    provider = await db.get(Provider, note.provider_id)
    if provider is None or provider.practice_id != note.practice_id or not provider.auto_approve:
        return False
    if not await _clean_findings(db, note) or await placement.awaiting_provider(db, note.id):
        return False
    return (await provider_eligibility(db, provider)).eligible


async def auto_approve(db: AsyncSession, note: Note) -> None:
    if not await auto_approve_eligible(db, note):
        raise Conflict("this note is not eligible for auto-approval")
    findings = await placement.current_findings(db, note)
    choices = choices_for(findings, await placement.current_decisions(db, note.id))
    codes = claim(await latest_codes(db, note.id, "billed"), findings, choices)
    if not codes:
        raise Conflict("there are no codes to bill")
    final_set = CodeSet(
        note_id=note.id,
        kind="final",
        revision=await next_revision(db, CodeSet, note.id, kind="final"),
        codes=[code.as_json() for code in codes],
        reason=AUTO_REASON,
        actor_id=None,
    )
    db.add(final_set)
    await db.flush()
    note.status, note.lane, note.lane_reason, note.headline = "approved", None, None, "Approved"
    note.approved_by, note.approved_at = None, utcnow()
    snapshot = await write_snapshot(db, note, final_set, AUTO_APPROVER, findings)
    detail = f"{format_code_list(codes)} · snapshot {snapshot.revision}"
    record_system_access(db, AUTO_ACTOR, note.practice_id, "approved", note_id=note.id, detail=detail[:300])


def _waiting_as_a_match(note: Note) -> bool:
    return (
        note.status == "ready"
        and note.lane == "approve"
        and note.lane_reason == MATCHES
        and note.flag_reason is None
        and note.flagged_by is None
        and note.compliance_cleared_by is None
    )


async def _clean_findings(db: AsyncSession, note: Note) -> bool:
    findings = await placement.current_findings(db, note)
    if any(item.action == "review" for item in findings):
        return False
    if any(item.kind == "audit_risk" and item.severity in SEVERE_AUDIT for item in findings):
        return False
    decisions = await placement.current_decisions(db, note.id)
    return not open_questions(findings, choices_for(findings, decisions))
