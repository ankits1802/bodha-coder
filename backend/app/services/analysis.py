from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.object_store import ObjectStore, analysis_response_key
from app.adapters.pdf_text import read_pdf_text
from app.ai.contracts import BilledCode, ModelClient, ReviewInputs, ReviewOutcome
from app.ai.prompts.context import labelled_addendum
from app.codes.billing_codes import Code
from app.codes.icd import IcdCatalog
from app.codes.mips_scope import practice_scope
from app.codes.places import setting_for
from app.models import Analysis, MipsList, Note, NoteText, Practice, Suggestion, utcnow
from app.services.code_sets import latest_codes, next_revision
from app.services.findings import Finding, build_findings
from app.services.note_texts import current_texts, note_texts
from app.services.placement import refresh_placement

SECTION_BY_CHECK = {"em": "em", "icd": "diagnoses", "cdi": "cdi", "audit": "audit", "mips": "mips", "hcc": "hcc"}
Reviewer = Callable[[ModelClient, ReviewInputs], Awaitable[ReviewOutcome]]


@dataclass(frozen=True)
class AnalysisDeps:
    review: Reviewer
    client: ModelClient
    store: ObjectStore
    icd: IcdCatalog


async def request_analysis(db: AsyncSession, note: Note, *, reason: str) -> Analysis:
    analysis = Analysis(note_id=note.id, revision=await next_revision(db, Analysis, note.id), reason=reason, context={})
    db.add(analysis)
    return analysis


async def claim_next(db: AsyncSession) -> Analysis | None:
    analysis = await db.scalar(
        select(Analysis)
        .where(Analysis.status == "queued", Analysis.requested_at <= utcnow())
        .order_by(Analysis.requested_at)
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    if analysis is None:
        return None
    analysis.status, analysis.started_at, analysis.attempts = "running", utcnow(), analysis.attempts + 1
    await db.execute(update(Note).where(Note.id == analysis.note_id, Note.status == "queued").values(status="reading"))
    await db.commit()
    return analysis


async def run_analysis(db: AsyncSession, analysis: Analysis, deps: AnalysisDeps) -> None:
    note = await db.get_one(Note, analysis.note_id)
    practice = await db.get_one(Practice, note.practice_id)
    source = await _note_source(db, note, deps.store)
    billed = await latest_codes(db, note.id, "billed")
    inputs = await _inputs(db, note, practice, billed, source)
    analysis.text_revision, analysis.context = source.revision, _context(inputs)
    outcome = await deps.review(deps.client, inputs)
    await _store_outcome(db, analysis, note, outcome, deps)
    if source.text is None and outcome.report.extracted_text:
        revision = await next_revision(db, NoteText, note.id)
        db.add(NoteText(note_id=note.id, revision=revision, source="document", text=outcome.report.extracted_text))
        analysis.text_revision = revision
    findings = build_findings(outcome.report, billed, deps.icd.for_service_date(note.service_date))
    await save_findings(db, analysis, findings)
    _adopt_patient(note, outcome)
    await refresh_placement(db, note)
    await db.commit()


@dataclass(frozen=True)
class NoteSource:
    text: str | None
    pdf: bytes | None
    revision: int | None


async def _note_source(db: AsyncSession, note: Note, store: ObjectStore) -> NoteSource:
    texts = await note_texts(db, note.id)
    current = current_texts(texts)
    pdf = await store.get(note.file_key)
    if current and current[0].text.strip():
        return NoteSource("\n\n".join(_labelled(text) for text in current), pdf, current[-1].revision)
    document = read_pdf_text(pdf)
    if not document.has_text_layer:
        return NoteSource(None, pdf, current[-1].revision if current else None)
    revision = texts[-1].revision + 1 if texts else 1
    db.add(NoteText(note_id=note.id, revision=revision, source="document", text=document.text))
    return NoteSource(document.text, pdf, revision)


def _labelled(text: NoteText) -> str:
    return text.text if text.source == "document" else labelled_addendum(text.revision, text.text)


async def _inputs(
    db: AsyncSession, note: Note, practice: Practice, billed: tuple[Code, ...], source: NoteSource
) -> ReviewInputs:
    sections = frozenset(
        SECTION_BY_CHECK[name] for name, on in practice.checks.items() if on and name in SECTION_BY_CHECK
    )
    if billed:
        sections = sections | {"code_review"}
    mips_list = await db.scalar(select(MipsList.measure_ids).where(MipsList.practice_id == practice.id))
    return ReviewInputs(
        sections=sections,
        setting=setting_for(note.place_code),
        place_of_service=note.place_code,
        visit_type=note.visit_type,
        service_date=note.service_date,
        billed_codes=tuple(BilledCode(code.code, code.type, code.modifiers, code.units) for code in billed),
        note_text=source.text,
        pdf=source.pdf,
        mips_scope=practice_scope(mips_list),
    )


def _context(inputs: ReviewInputs) -> dict[str, Any]:
    return {
        "sections": sorted(inputs.sections),
        "setting": inputs.setting,
        "place_of_service": inputs.place_of_service,
        "visit_type": inputs.visit_type,
        "billed": [code.code for code in inputs.billed_codes],
        "mips_measures": list(inputs.mips_scope.measure_ids) if inputs.mips_scope else None,
        "source": "pdf" if inputs.note_text is None else "text and pdf" if inputs.pdf else "text",
    }


async def _store_outcome(
    db: AsyncSession, analysis: Analysis, note: Note, outcome: ReviewOutcome, deps: AnalysisDeps
) -> None:
    key = analysis_response_key(note.practice_id, note.id, analysis.revision)
    replies = [{"model": reply.model, "text": reply.text} for reply in outcome.replies]
    await deps.store.put(key, json.dumps({"replies": replies}).encode(), content_type="application/json")
    await db.execute(
        update(Analysis).where(Analysis.note_id == note.id, Analysis.status == "succeeded").values(status="superseded")
    )
    analysis.status, analysis.finished_at, analysis.response_key = "succeeded", utcnow(), key
    analysis.report = outcome.report.model_dump(mode="json")
    analysis.model = outcome.replies[-1].model if outcome.replies else None
    analysis.prompt_version = outcome.prompt_version
    analysis.input_tokens = sum(reply.input_tokens for reply in outcome.replies)
    analysis.output_tokens = sum(reply.output_tokens for reply in outcome.replies)
    analysis.context = {**analysis.context, "failed_sections": sorted(outcome.failed_sections)}
    note.current_analysis_id = analysis.id


async def save_findings(db: AsyncSession, analysis: Analysis, findings: list[Finding]) -> None:
    for finding in findings:
        db.add(
            Suggestion(
                analysis_id=analysis.id,
                note_id=analysis.note_id,
                kind=finding.kind,
                key=finding.key,
                code_before=finding.code_before,
                code_after=finding.code_after,
                action=finding.action,
                title=finding.title[:300],
                reasoning=finding.reasoning,
                evidence=list(finding.evidence),
                severity=finding.severity,
                detail={**finding.detail, "default_choice": finding.default_choice},
            )
        )


def _adopt_patient(note: Note, outcome: ReviewOutcome) -> None:
    patient = outcome.report.patient
    note.patient_name = note.patient_name or patient.name
    note.patient_age = note.patient_age if note.patient_age is not None else patient.age
    note.patient_sex = note.patient_sex or patient.sex
    if note.patient_birth_date is None and patient.birth_date is not None and patient.birth_date <= note.service_date:
        note.patient_birth_date = patient.birth_date


async def fail_attempt(db: AsyncSession, analysis: Analysis, error: str, *, retry_in: timedelta | None) -> None:
    analysis.error = error[:300]
    if retry_in is not None:
        analysis.status, analysis.requested_at = "queued", utcnow() + retry_in
    else:
        analysis.status, analysis.finished_at = "failed", utcnow()
        await db.execute(
            update(Note).where(Note.id == analysis.note_id, Note.status == "reading").values(status="failed")
        )
    await db.commit()


async def stale_running(db: AsyncSession, *, older_than: timedelta) -> list[Analysis]:
    return list(
        (
            await db.scalars(
                select(Analysis).where(Analysis.status == "running", Analysis.started_at < utcnow() - older_than)
            )
        ).all()
    )
