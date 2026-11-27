from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.messenger import Messenger
from app.adapters.seal_keys import RecordSigner
from app.codes.billing_codes import Code
from app.core.deps import Actor
from app.core.errors import Conflict, Forbidden, Invalid
from app.models import AddendumRequest, CodeSet, Decision, Note, utcnow
from app.services.audit_log import record_access
from app.services.claim_snapshots import approver_of, write_snapshot
from app.services.code_sets import next_revision
from app.services.findings import Finding
from app.services.level_changes import ask_level_confirmation
from app.services.note_returns import ReturnReason, return_to_coder, undecided_items
from app.services.override_reasons import OTHER_REASON, OverrideReason, Reasoned, checked_reason, missing_reasons
from app.services.placement import current_findings
from app.services.review_actions import current_claim, new_decision, note_for, open_note
from app.services.sealed_records import APPROVAL_EVENT, COMPLIANCE_EVENT
from app.services.sealing import person_signer, seal_snapshot
from app.services.signatures import person_signature

__all__ = ["SIGNED_STATEMENTS", "approve", "approve_many", "compliance_decision", "latest_reasoned"]

MISSING_REASONS = "choose a reason for each choice that departs from Bodha before approving"
UNDECIDED_RETURN = "decide again on what compliance returned before approving"
RETURNED_ALONE = "a note returned by compliance is approved on its own"
NO_RETURN_REASON = "choose why the note goes back to the coder"
SIGNED_STATEMENTS = {
    "approved": "I approve this claim as coded from the documentation.",
    "compliance confirm": "I confirm this claim after compliance review.",
    "compliance keep": "I keep the billed visit level after compliance review.",
}


async def approve(
    db: AsyncSession,
    messenger: Messenger,
    signer: RecordSigner,
    actor: Actor,
    note_id: str,
    *,
    reason: str = "approved",
    event: str = APPROVAL_EVENT,
) -> Note:
    note = await open_note(db, actor, note_id)
    signature = await person_signature(db, actor)
    findings = await current_findings(db, note)
    await _refuse_unready(db, note, findings)
    codes = await current_claim(db, note)
    if not codes:
        raise Conflict("there are no codes to bill")
    final_set = await _final_set(db, actor, note, codes, reason)
    note.status, note.lane, note.lane_reason, note.headline = "approved", None, None, "Approved"
    note.approved_by, note.approved_at, note.returned_at = actor.user.id, utcnow(), None
    snapshot = await write_snapshot(db, note, final_set, approver_of(actor), findings)
    signed_by = person_signer(actor, signature)
    await seal_snapshot(db, signer, signed_by, snapshot, event=event, statement=SIGNED_STATEMENTS[reason])
    detail = f"{', '.join(code.label() for code in codes)} · snapshot {snapshot.revision}"
    record_access(db, actor, "approved", note_id=note.id, detail=detail[:300])
    await ask_level_confirmation(db, messenger, actor, note, snapshot=snapshot, findings=findings)
    await db.commit()
    return note


async def approve_many(
    db: AsyncSession, messenger: Messenger, signer: RecordSigner, actor: Actor, note_ids: list[str]
) -> list[str]:
    await person_signature(db, actor)
    approved: list[str] = []
    for note_id in note_ids:
        note = await note_for(db, actor, note_id)
        if note.returned_at is not None:
            raise Conflict(RETURNED_ALONE)
        if note.lane != "approve":
            raise Conflict("only notes whose codes match the note can be approved together")
        await approve(db, messenger, signer, actor, note_id)
        approved.append(note_id)
    return approved


async def compliance_decision(
    db: AsyncSession,
    messenger: Messenger,
    signer: RecordSigner,
    actor: Actor,
    note_id: str,
    *,
    decision: str,
    reason: str | None,
    override: OverrideReason | None = None,
    returned: ReturnReason | None = None,
) -> Note:
    note = await open_note(db, actor, note_id)
    if note.lane != "compliance":
        raise Conflict("this note is not waiting for compliance")
    if note.flagged_by == actor.user.id:
        raise Forbidden("a note can't be cleared by the person who flagged it")
    if decision == "return":
        if returned is None:
            raise Invalid(NO_RETURN_REASON)
        await return_to_coder(db, actor, note, returned)
        await db.commit()
        return note
    if decision == "keep":
        if not reason:
            raise Invalid("explain why the billed level is kept")
        kept = override or checked_reason(OTHER_REASON, reason)
        db.add(new_decision(note, actor, "em", "keep", kept))
        await db.flush()
    if reason:
        record_access(db, actor, f"compliance {decision}", note_id=note.id, detail=reason)
    note.compliance_cleared_by = actor.user.id
    reason_given = f"compliance {decision}"
    return await approve(db, messenger, signer, actor, note_id, reason=reason_given, event=COMPLIANCE_EVENT)


async def latest_reasoned(db: AsyncSession, note_id: str) -> dict[str, Reasoned]:
    rows = await db.execute(
        select(Decision.suggestion_key, Decision.choice, Decision.override_reason)
        .where(Decision.note_id == note_id)
        .order_by(Decision.created_at)
    )
    return {key: Reasoned(key, choice, reason) for key, choice, reason in rows.all()}


async def _refuse_unready(db: AsyncSession, note: Note, findings: list[Finding]) -> None:
    if any(item.action == "review" and item.code_before for item in findings):
        raise Conflict("fix the billed codes Bodha could not confirm before approving")
    if await _held_for_provider(db, note.id):
        raise Conflict("this claim is held until the provider answers")
    missing = missing_reasons(findings, await latest_reasoned(db, note.id))
    if missing:
        raise Conflict(f"{MISSING_REASONS}: {', '.join(missing)}")
    if await undecided_items(db, note, findings):
        raise Conflict(UNDECIDED_RETURN)


async def _final_set(db: AsyncSession, actor: Actor, note: Note, codes: tuple[Code, ...], reason: str) -> CodeSet:
    final_set = CodeSet(
        note_id=note.id,
        kind="final",
        revision=await next_revision(db, CodeSet, note.id, kind="final"),
        codes=[code.as_json() for code in codes],
        reason=reason,
        actor_id=actor.user.id,
        actor_role=actor.role,
    )
    db.add(final_set)
    await db.flush()
    return final_set


async def _held_for_provider(db: AsyncSession, note_id: str) -> bool:
    held = await db.scalar(
        select(AddendumRequest.id).where(
            AddendumRequest.note_id == note_id, AddendumRequest.status == "sent", AddendumRequest.hold_claim.is_(True)
        )
    )
    return held is not None
