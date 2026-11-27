from __future__ import annotations

import json
from datetime import timedelta
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.object_store import ObjectStore
from app.adapters.pdf_text import DocumentUnreadable
from app.ai.contracts import BilledCode, ReviewInputs, ReviewOutcome, ReviewReport
from app.ai.errors import ModelError
from app.codes.billing_codes import Code
from app.codes.icd import IcdRelease, IcdReleaseUnavailable
from app.codes.mips_scope import practice_scope
from app.codes.places import setting_for
from app.models import Analysis, EvalCase, EvalRun, Note, NoteText, utcnow
from app.services.agreement import compare_elements, elements_from_json, elements_of
from app.services.analysis import AnalysisDeps, latest_codes
from app.services.evaluation_scores import evaluation_summary
from app.services.findings import build_findings
from app.services.note_texts import current_texts, note_texts
from app.services.routing import choices_for, claim

__all__ = [
    "RUNS_PER_CASE",
    "CaseUnavailable",
    "evaluation_response_key",
    "fail_evaluation",
    "fail_stale_evaluations",
    "next_queued_evaluation",
    "run_evaluation",
    "run_next_evaluation",
]

RUNS_PER_CASE = 2
ERROR_LENGTH = 300
CASE_FAILURES = (ModelError, DocumentUnreadable, IcdReleaseUnavailable)


class CaseUnavailable(Exception):
    pass


def evaluation_response_key(practice_id: str, run_id: str, case_id: str, attempt: int) -> str:
    return f"practices/{practice_id}/evaluations/{run_id}/{case_id}-{attempt}.json"


async def next_queued_evaluation(db: AsyncSession) -> str | None:
    return await db.scalar(
        select(EvalRun.id).where(EvalRun.status == "queued").order_by(EvalRun.created_at, EvalRun.id).limit(1)
    )


async def run_next_evaluation(db: AsyncSession, deps: AnalysisDeps) -> bool:
    run_id = await next_queued_evaluation(db)
    return run_id is not None and await run_evaluation(db, run_id, deps)


async def run_evaluation(db: AsyncSession, run_id: str, deps: AnalysisDeps) -> bool:
    run = await _claim(db, run_id)
    if run is None:
        return False
    cases = list(
        await db.scalars(
            select(EvalCase).where(EvalCase.practice_id == run.practice_id).order_by(EvalCase.created_at, EvalCase.id)
        )
    )
    results: list[dict[str, Any]] = []
    for case in cases:
        results.append(await _evaluate_case(db, run, case, deps))
        run.results = list(results)
        await db.commit()
    models = sorted({result["model"] for result in results if result.get("model")})
    run.results, run.summary = results, evaluation_summary(results)
    run.model = ", ".join(models)[:80] or run.model
    run.status, run.finished_at = ("done" if run.summary["scored"] else "failed"), utcnow()
    await db.commit()
    return True


async def fail_evaluation(db: AsyncSession, run_id: str, reason: str) -> None:
    run = await db.get_one(EvalRun, run_id)
    run.status, run.finished_at = "failed", utcnow()
    run.summary = {**run.summary, "error": reason[:ERROR_LENGTH]}
    await db.commit()


async def fail_stale_evaluations(db: AsyncSession, *, older_than: timedelta) -> int:
    stale = await db.execute(
        update(EvalRun)
        .where(EvalRun.status == "running", EvalRun.created_at < utcnow() - older_than)
        .values(status="failed", finished_at=utcnow(), summary={"error": "worker stopped while running"})
    )
    await db.commit()
    return stale.rowcount or 0


async def _claim(db: AsyncSession, run_id: str) -> EvalRun | None:
    run = await db.scalar(
        select(EvalRun).where(EvalRun.id == run_id, EvalRun.status == "queued").with_for_update(skip_locked=True)
    )
    if run is None:
        await db.rollback()
        return None
    run.status = "running"
    await db.commit()
    return run


async def _evaluate_case(db: AsyncSession, run: EvalRun, case: EvalCase, deps: AnalysisDeps) -> dict[str, Any]:
    note = await db.get_one(Note, case.note_id)
    base = {"case_id": case.id, "note_id": note.id, "expected": case.expected}
    try:
        inputs, billed = await _case_inputs(db, note, deps.store)
        release = deps.icd.for_service_date(note.service_date)
        await db.commit()
        outcomes = [await deps.review(deps.client, inputs) for _ in range(RUNS_PER_CASE)]
    except (CaseUnavailable, *CASE_FAILURES) as error:
        return {**base, "error": (str(error) or type(error).__name__)[:ERROR_LENGTH]}
    await _store_replies(deps.store, run, case, outcomes)
    suggested = [elements_of(_suggested_claim(outcome.report, billed, release)) for outcome in outcomes]
    replies = [reply for outcome in outcomes for reply in outcome.replies]
    return {
        **base,
        "model": replies[-1].model if replies else None,
        "prompt_version": outcomes[0].prompt_version,
        "input_tokens": sum(reply.input_tokens for reply in replies),
        "output_tokens": sum(reply.output_tokens for reply in replies),
        "runs": [elements.as_json() for elements in suggested],
        "agreement": compare_elements(elements_from_json(case.expected), suggested[0]),
        "repeat": compare_elements(suggested[0], suggested[1]),
    }


async def _case_inputs(db: AsyncSession, note: Note, store: ObjectStore) -> tuple[ReviewInputs, tuple[Code, ...]]:
    analysis = await db.get(Analysis, note.current_analysis_id) if note.current_analysis_id else None
    sections = (analysis.context or {}).get("sections") if analysis else None
    if analysis is None or not sections:
        raise CaseUnavailable("this note has no review to repeat")
    billed = await latest_codes(db, note.id, "billed")
    text = _note_text(current_texts(await note_texts(db, note.id)))
    inputs = ReviewInputs(
        sections=frozenset(sections),
        setting=setting_for(note.place_code),
        place_of_service=note.place_code,
        visit_type=note.visit_type,
        service_date=note.service_date,
        billed_codes=tuple(BilledCode(code.code, code.type, code.modifiers) for code in billed),
        note_text=text,
        pdf=None if text else await store.get(note.file_key),
        mips_scope=practice_scope(analysis.context.get("mips_measures")),
    )
    return inputs, billed


def _note_text(texts: list[NoteText]) -> str | None:
    if not texts or not texts[0].text.strip():
        return None
    return "\n\n".join(
        text.text if text.source == "document" else f"ADDENDUM (revision {text.revision}):\n{text.text}"
        for text in texts
    )


def _suggested_claim(report: ReviewReport, billed: tuple[Code, ...], release: IcdRelease) -> tuple[Code, ...]:
    findings = build_findings(report, billed, release)
    return claim(billed, findings, choices_for(findings, {}))


async def _store_replies(store: ObjectStore, run: EvalRun, case: EvalCase, outcomes: list[ReviewOutcome]) -> None:
    for attempt, outcome in enumerate(outcomes, start=1):
        replies = [{"model": reply.model, "text": reply.text} for reply in outcome.replies]
        key = evaluation_response_key(run.practice_id, run.id, case.id, attempt)
        await store.put(key, json.dumps({"replies": replies}).encode(), content_type="application/json")
