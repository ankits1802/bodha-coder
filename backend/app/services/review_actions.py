from __future__ import annotations

from collections.abc import Mapping, Sequence

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.contracts import ReviewReport
from app.codes.billing_codes import Code, InvalidPointers, format_code_list, parse_code_list, with_pointers
from app.codes.icd import IcdCatalog, format_icd
from app.core.deps import Actor
from app.core.errors import Conflict, Invalid, NotFound
from app.models import LEVEL_CHANGE_PURPOSE, AddendumRequest, Analysis, CodeSet, Decision, Note, utcnow
from app.services.analysis import latest_codes, next_revision, request_analysis, save_findings
from app.services.analysis_records import billed_context
from app.services.audit_log import record_access
from app.services.findings import Finding, build_findings
from app.services.note_change_history import record_note_change
from app.services.override_reasons import OverrideReason, departs_from_bodha, reason_text
from app.services.payers import payer_changed
from app.services.placement import current_decisions, current_findings, refresh_placement
from app.services.pointer_decisions import POINTER_CHOICE, POINTER_KEY, pointer_key, read_pointer_key
from app.services.routing import choices_for, claim

INFO_KINDS = ("cdi_gap", "audit_risk", "audit_finding", "mips")
RETRY_LIMIT = 500
PAYER_READ = "payer"
OVERRIDE_ACTION = "override reason"


def allowed_choices(finding: Finding) -> tuple[str, ...]:
    if finding.kind in INFO_KINDS or finding.action in ("keep", "review", "not_applicable", "info"):
        return ("keep",)
    if finding.kind == "cdi_query":
        return ("ask", "skip")
    if finding.action == "add":
        return ("add", "skip") if finding.kind == "diagnosis" else ("accept", "keep")
    if finding.action == "ask":
        return ("ask", "keep") if finding.code_before else ("ask", "skip")
    return ("accept", "keep")


async def note_for(db: AsyncSession, actor: Actor, note_id: str) -> Note:
    note = await db.get(Note, note_id)
    if note is None or note.practice_id != actor.practice_id:
        raise NotFound("note not found")
    return note


def new_decision(note: Note, actor: Actor, key: str, choice: str, reason: OverrideReason | None) -> Decision:
    return Decision(
        note_id=note.id,
        analysis_id=note.current_analysis_id,
        suggestion_key=key,
        choice=choice,
        actor_id=actor.user.id,
        actor_role=actor.role,
        override_reason=reason.reason if reason else None,
        override_note=reason.note if reason else None,
    )


async def decide(
    db: AsyncSession,
    actor: Actor,
    note_id: str,
    choices: Mapping[str, str],
    reasons: Mapping[str, OverrideReason] | None = None,
) -> Note:
    note = await open_note(db, actor, note_id)
    findings = {finding.key: finding for finding in await current_findings(db, note)}
    given = dict(reasons or {})
    stray = sorted(set(given) - set(choices))
    if stray:
        raise Invalid(f"a reason needs a choice: {', '.join(stray)}")
    for key, choice in choices.items():
        finding = _decidable(findings, key, choice)
        reason = given.get(key)
        if reason is not None and not departs_from_bodha(finding, choice):
            raise Invalid(f"{choice} on {key} follows Bodha and takes no override reason")
        db.add(new_decision(note, actor, key, choice, reason))
        if reason is not None:
            record_access(db, actor, OVERRIDE_ACTION, note_id=note.id, detail=override_detail(key, choice, reason))
    await db.flush()
    await refresh_placement(db, note)
    await db.commit()
    return note


def override_detail(subject: str, choice: str | None, reason: OverrideReason) -> str:
    said = reason_text(reason.reason, reason.note) or ""
    return " · ".join(part for part in (subject, choice, said) if part)[:300]


def _decidable(findings: Mapping[str, Finding], key: str, choice: str) -> Finding:
    finding = findings.get(key)
    if finding is None:
        raise Invalid(f"unknown suggestion {key}")
    if choice not in allowed_choices(finding):
        raise Invalid(f"{choice} is not allowed for {key}")
    return finding


async def current_claim(db: AsyncSession, note: Note) -> tuple[Code, ...]:
    findings = await current_findings(db, note)
    choices = choices_for(findings, await current_decisions(db, note.id))
    derived = claim(await latest_codes(db, note.id, "billed"), findings, choices)
    return with_pointers(derived, await stored_pointers(db, note.id))


async def stored_pointers(db: AsyncSession, note_id: str) -> dict[str, tuple[str, ...]]:
    keys = await db.scalars(
        select(Decision.suggestion_key)
        .where(Decision.note_id == note_id, Decision.suggestion_key.startswith(POINTER_KEY))
        .order_by(Decision.created_at)
    )
    return dict(parsed for key in keys if (parsed := read_pointer_key(key)) is not None)


async def save_pointers(
    db: AsyncSession, actor: Actor, note_id: str, lines: Sequence[tuple[str, Sequence[str]]], reason: OverrideReason
) -> Note:
    note = await open_note(db, actor, note_id)
    linked = _checked_pointers(await current_claim(db, note), lines)
    for code, pointers in linked.items():
        db.add(new_decision(note, actor, pointer_key(code, pointers), POINTER_CHOICE, reason))
    detail = "; ".join(f"{code} {' '.join(pointers)}".strip() for code, pointers in linked.items())
    record_access(db, actor, "linked diagnoses", note_id=note.id, detail=override_detail(detail, None, reason))
    await db.commit()
    return note


async def flag(db: AsyncSession, actor: Actor, note_id: str, reason: str) -> Note:
    note = await open_note(db, actor, note_id)
    flagged = reason.strip()[:2000]
    record_note_change(db, actor, note, "flag", old=note.flag_reason, new=flagged)
    note.flag_reason, note.flagged_by, note.compliance_cleared_by = flagged, actor.user.id, None
    note.returned_at = None
    await refresh_placement(db, note)
    record_access(db, actor, "flagged for compliance", note_id=note.id, detail=reason.strip()[:300])
    await db.commit()
    return note


async def update_billed(
    db: AsyncSession, actor: Actor, note_id: str, text: str, icd: IcdCatalog, *, reason: OverrideReason
) -> Note:
    note = await open_note(db, actor, note_id)
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
            actor_role=actor.role,
            override_reason=reason.reason,
            override_note=reason.note,
        )
    )
    current = await db.get(Analysis, note.current_analysis_id) if note.current_analysis_id else None
    if current is None or current.report is None:
        raise Conflict("Bodha has not finished reading this note")
    await _rederive(db, note, current, parsed.codes, icd)
    labels = format_code_list(parsed.codes)
    record_access(db, actor, "edited billed codes", note_id=note.id, detail=override_detail(labels, None, reason))
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
        context={**current.context, "billed": billed_context(billed)},
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
    reason = await _read_again_reason(db, actor, note)
    note.status = "queued"
    await request_analysis(db, note, reason=reason)
    if reason == PAYER_READ:
        record_access(db, actor, "read again with payer", note_id=note.id)
    await db.commit()
    return note


async def _read_again_reason(db: AsyncSession, actor: Actor, note: Note) -> str:
    if note.status == "failed":
        return "retry"
    if note.status != "ready":
        raise Conflict("only notes that could not be read can be retried")
    analysis = await db.get(Analysis, note.current_analysis_id) if note.current_analysis_id else None
    if not payer_changed(actor.practice, note, analysis):
        raise Conflict("the payer has not changed since this note was read")
    return PAYER_READ


async def reopen(db: AsyncSession, actor: Actor, note_id: str) -> Note:
    note = await note_for(db, actor, note_id)
    await reopen_note(db, actor, note)
    await db.commit()
    return note


async def reopen_many(db: AsyncSession, actor: Actor, note_ids: list[str]) -> list[str]:
    notes = [await note_for(db, actor, note_id) for note_id in dict.fromkeys(note_ids)]
    for note in notes:
        await reopen_note(db, actor, note)
    await db.commit()
    return [note.id for note in notes]


async def reopen_note(db: AsyncSession, actor: Actor, note: Note) -> None:
    if note.status != "approved":
        raise Conflict("only an approved note that has not been exported can be reopened")
    note.status, note.approved_by, note.approved_at = "ready", None, None
    await cancel_level_confirmations(db, note.id)
    await refresh_placement(db, note)
    record_access(db, actor, "reopened", note_id=note.id)


async def cancel_level_confirmations(db: AsyncSession, note_id: str) -> None:
    await db.execute(
        update(AddendumRequest)
        .where(
            AddendumRequest.note_id == note_id,
            AddendumRequest.purpose == LEVEL_CHANGE_PURPOSE,
            AddendumRequest.status == "sent",
        )
        .values(status="cancelled", remind_at=None)
    )


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


def _checked_pointers(
    codes: tuple[Code, ...], lines: Sequence[tuple[str, Sequence[str]]]
) -> dict[str, tuple[str, ...]]:
    procedures = {code.code for code in codes if code.type == "CPT"}
    diagnoses = {code.code for code in codes if code.type == "ICD-10"}
    checked: dict[str, tuple[str, ...]] = {}
    for named, pointers in lines:
        code = named.strip().upper()
        if code not in procedures:
            raise Invalid(f"{code} is not a procedure line of the claim")
        if code in checked:
            raise Invalid(f"{code} is listed twice")
        linked = tuple(format_icd(pointer) for pointer in pointers)
        unknown = [pointer for pointer in linked if pointer not in diagnoses]
        if unknown:
            raise Invalid(f"{', '.join(unknown)} is not a diagnosis on the claim")
        try:
            checked[code] = Code(code, "CPT", pointers=linked).pointers
        except InvalidPointers as error:
            raise Invalid(str(error)) from error
    return checked


async def open_note(db: AsyncSession, actor: Actor, note_id: str) -> Note:
    note = await note_for(db, actor, note_id)
    if note.status != "ready":
        raise Conflict("this note is not open for review")
    return note
