from __future__ import annotations

from collections.abc import Mapping

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.contracts import ReviewReport
from app.codes.billing_codes import Code, parse_code_list
from app.codes.icd import IcdCatalog
from app.core.deps import Actor
from app.core.errors import Conflict, Forbidden, Invalid, NotFound
from app.models import AddendumRequest, Analysis, CodeSet, Decision, Note, utcnow
from app.services.analysis import latest_codes, next_revision, request_analysis, save_findings
from app.services.audit_log import record_access
from app.services.findings import Finding, build_findings
from app.services.placement import current_decisions, current_findings, refresh_placement
from app.services.routing import choices_for, claim

INFO_KINDS = ("cdi_gap", "audit_risk", "audit_finding", "mips")
RETRY_LIMIT = 500


def allowed_choices(finding: Finding) -> tuple[str, ...]:
    if finding.kind in INFO_KINDS or finding.action in ("keep", "review", "not_applicable", "info"):
        return ("keep",)
    if finding.kind == "cdi_query":
        return ("ask", "skip")
    if finding.action == "add":
        return ("add", "skip")
    if finding.action == "ask":
        return ("ask", "keep") if finding.code_before else ("ask", "skip")
    return ("accept", "keep")


async def note_for(db: AsyncSession, actor: Actor, note_id: str) -> Note:
    note = await db.get(Note, note_id)
    if note is None or note.practice_id != actor.practice_id:
        raise NotFound("note not found")
    return note


async def decide(db: AsyncSession, actor: Actor, note_id: str, choices: Mapping[str, str]) -> Note:
    note = await _open_note(db, actor, note_id)
    findings = {finding.key: finding for finding in await current_findings(db, note)}
    for key, choice in choices.items():
        finding = findings.get(key)
        if finding is None:
            raise Invalid(f"unknown suggestion {key}")
        if choice not in allowed_choices(finding):
            raise Invalid(f"{choice} is not allowed for {key}")
        db.add(
            Decision(
                note_id=note.id,
                analysis_id=note.current_analysis_id,
                suggestion_key=key,
                choice=choice,
                actor_id=actor.user.id,
            )
        )
    await db.flush()
    await refresh_placement(db, note)
    await db.commit()
    return note


async def current_claim(db: AsyncSession, note: Note) -> tuple[Code, ...]:
    findings = await current_findings(db, note)
    choices = choices_for(findings, await current_decisions(db, note.id))
    return claim(await latest_codes(db, note.id, "billed"), findings, choices)


async def approve(db: AsyncSession, actor: Actor, note_id: str, *, reason: str = "approved") -> Note:
    note = await _open_note(db, actor, note_id)
    findings = await current_findings(db, note)
    if any(item.action == "review" and item.code_before for item in findings):
        raise Conflict("fix the billed codes Bodha could not confirm before approving")
    if await _held_for_provider(db, note.id):
        raise Conflict("this claim is held until the provider answers")
    codes = await current_claim(db, note)
    if not codes:
        raise Conflict("there are no codes to bill")
    db.add(
        CodeSet(
            note_id=note.id,
            kind="final",
            revision=await next_revision(db, CodeSet, note.id, kind="final"),
            codes=[code.as_json() for code in codes],
            reason=reason,
            actor_id=actor.user.id,
        )
    )
    note.status, note.lane, note.lane_reason, note.headline = "approved", None, None, "Approved"
    note.approved_by, note.approved_at = actor.user.id, utcnow()
    record_access(db, actor, "approved", note_id=note.id, detail=", ".join(code.label() for code in codes))
    await db.commit()
    return note


async def approve_many(db: AsyncSession, actor: Actor, note_ids: list[str]) -> list[str]:
    approved: list[str] = []
    for note_id in note_ids:
        note = await note_for(db, actor, note_id)
        if note.lane != "approve":
            raise Conflict("only notes whose codes match the note can be approved together")
        await approve(db, actor, note_id)
        approved.append(note_id)
    return approved


async def flag(db: AsyncSession, actor: Actor, note_id: str, reason: str) -> Note:
    note = await _open_note(db, actor, note_id)
    note.flag_reason, note.flagged_by, note.compliance_cleared_by = reason.strip()[:2000], actor.user.id, None
    await refresh_placement(db, note)
    record_access(db, actor, "flagged for compliance", note_id=note.id)
    await db.commit()
    return note


async def compliance_decision(
    db: AsyncSession, actor: Actor, note_id: str, *, decision: str, reason: str | None
) -> Note:
    note = await _open_note(db, actor, note_id)
    if note.lane != "compliance":
        raise Conflict("this note is not waiting for compliance")
    if note.flagged_by == actor.user.id:
        raise Forbidden("a note can't be cleared by the person who flagged it")
    if decision == "return":
        note.flag_reason, note.compliance_cleared_by = None, actor.user.id
        await refresh_placement(db, note)
        record_access(db, actor, "returned to coder", note_id=note.id, detail=reason)
        await db.commit()
        return note
    if decision == "keep":
        if not reason:
            raise Invalid("explain why the billed level is kept")
        db.add(
            Decision(
                note_id=note.id,
                analysis_id=note.current_analysis_id,
                suggestion_key="em",
                choice="keep",
                actor_id=actor.user.id,
            )
        )
        await db.flush()
    note.compliance_cleared_by = actor.user.id
    return await approve(
        db, actor, note_id, reason=f"compliance {decision}: {reason}" if reason else f"compliance {decision}"
    )


async def update_billed(db: AsyncSession, actor: Actor, note_id: str, text: str, icd: IcdCatalog) -> Note:
    note = await _open_note(db, actor, note_id)
    parsed = parse_code_list(text)
    if parsed.invalid:
        raise Invalid(f"not valid codes: {', '.join(parsed.invalid)}")
    db.add(
        CodeSet(
            note_id=note.id,
            kind="billed",
            revision=await next_revision(db, CodeSet, note.id, kind="billed"),
            codes=[code.as_json() for code in parsed.codes],
            reason="edited",
            actor_id=actor.user.id,
        )
    )
    current = await db.get(Analysis, note.current_analysis_id) if note.current_analysis_id else None
    if current is None or current.report is None:
        raise Conflict("Bodha has not finished reading this note")
    await _rederive(db, note, current, parsed.codes, icd)
    record_access(db, actor, "edited billed codes", note_id=note.id)
    await db.commit()
    return note


async def _rederive(db: AsyncSession, note: Note, current: Analysis, billed: tuple[Code, ...], icd: IcdCatalog) -> None:
    revision = await next_revision(db, Analysis, note.id)
    current.status = "superseded"
    derived = Analysis(
        note_id=note.id,
        revision=revision,
        reason="billed_codes",
        status="succeeded",
        text_revision=current.text_revision,
        context={**current.context, "billed": [c.code for c in billed]},
        model=current.model,
        prompt_version=current.prompt_version,
        response_key=current.response_key,
        report=current.report,
        started_at=utcnow(),
        finished_at=utcnow(),
    )
    db.add(derived)
    await db.flush()
    note.current_analysis_id = derived.id
    findings = build_findings(
        ReviewReport.model_validate(current.report), billed, icd.for_service_date(note.service_date)
    )
    await save_findings(db, derived, findings)
    await db.flush()
    await refresh_placement(db, note)


async def retry(db: AsyncSession, actor: Actor, note_id: str) -> Note:
    note = await note_for(db, actor, note_id)
    if note.status != "failed":
        raise Conflict("only notes that could not be read can be retried")
    note.status = "queued"
    await request_analysis(db, note, reason="retry")
    await db.commit()
    return note


async def retry_failed(db: AsyncSession, actor: Actor, note_ids: list[str] | None) -> list[str]:
    query = select(Note).where(Note.practice_id == actor.practice_id, Note.status == "failed").limit(RETRY_LIMIT)
    if note_ids is not None:
        query = query.where(Note.id.in_(note_ids))
    notes = list((await db.scalars(query)).all())
    for note in notes:
        note.status = "queued"
        await request_analysis(db, note, reason="retry")
    if notes:
        record_access(db, actor, "asked to read again", detail=f"{len(notes)} notes")
    await db.commit()
    return [note.id for note in notes]


async def _open_note(db: AsyncSession, actor: Actor, note_id: str) -> Note:
    note = await note_for(db, actor, note_id)
    if note.status != "ready":
        raise Conflict("this note is not open for review")
    return note


async def _held_for_provider(db: AsyncSession, note_id: str) -> bool:
    held = await db.scalar(
        select(AddendumRequest.id).where(
            AddendumRequest.note_id == note_id, AddendumRequest.status == "sent", AddendumRequest.hold_claim.is_(True)
        )
    )
    return held is not None
