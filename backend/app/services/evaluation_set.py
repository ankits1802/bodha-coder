from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.review import PROMPT_VERSION
from app.codes.billing_codes import Code
from app.core.config import get_settings
from app.core.deps import Actor
from app.core.errors import Conflict, NotFound
from app.models import EvalCase, EvalRun, Note, Provider
from app.services.agreement import elements_of, em_level
from app.services.analysis import latest_codes
from app.services.audit_log import record_activity
from app.services.evaluation_scores import run_change
from app.services.placement import SETTLED_STATUSES
from app.services.review_actions import note_for

__all__ = [
    "ACTIVE_RUN_STATUSES",
    "CANDIDATE_LIMIT",
    "case_candidates",
    "evaluation_cases",
    "evaluation_runs",
    "expected_for",
    "mark_case",
    "queue_run",
    "remove_case",
    "run_detail",
]

CANDIDATE_LIMIT = 50
ACTIVE_RUN_STATUSES = ("queued", "running")


def expected_for(codes: Sequence[Code]) -> dict[str, Any]:
    elements = elements_of(codes)
    return {**elements.as_json(), "level": em_level(elements.em), "claim": [code.as_json() for code in codes]}


async def mark_case(db: AsyncSession, actor: Actor, note_id: str) -> dict[str, Any]:
    note = await note_for(db, actor, note_id)
    if note.status not in SETTLED_STATUSES:
        raise Conflict("only an approved note can join the evaluation set")
    final = await latest_codes(db, note.id, "final")
    if not final or note.current_analysis_id is None:
        raise Conflict("this note has no approved claim to compare with")
    known = await db.scalar(
        select(EvalCase.id).where(EvalCase.practice_id == actor.practice_id, EvalCase.note_id == note.id)
    )
    if known is not None:
        raise Conflict("this note is already in the evaluation set")
    case = EvalCase(
        practice_id=actor.practice_id,
        note_id=note.id,
        expected={**expected_for(final), "analysis_id": note.current_analysis_id},
        created_by=actor.user.id,
    )
    db.add(case)
    record_activity(db, actor, "added evaluation case", practice_id=actor.practice_id, detail=note.id)
    await db.commit()
    return {"id": case.id, "note_id": note.id}


async def remove_case(db: AsyncSession, actor: Actor, note_id: str) -> None:
    removed = await db.execute(
        delete(EvalCase).where(EvalCase.practice_id == actor.practice_id, EvalCase.note_id == note_id)
    )
    if not removed.rowcount:
        raise NotFound("this note is not in the evaluation set")
    record_activity(db, actor, "removed evaluation case", practice_id=actor.practice_id, detail=note_id)
    await db.commit()


async def evaluation_cases(db: AsyncSession, actor: Actor) -> list[dict[str, Any]]:
    rows = await db.execute(
        select(EvalCase, Note.service_date, Provider.name)
        .join(Note, Note.id == EvalCase.note_id)
        .join(Provider, Provider.id == Note.provider_id)
        .where(EvalCase.practice_id == actor.practice_id)
        .order_by(EvalCase.created_at.desc())
    )
    return [
        {
            "note_id": case.note_id,
            "provider_name": provider_name,
            "service_date": service_date.isoformat(),
            "em": case.expected.get("em"),
            "level": case.expected.get("level"),
            "icd": case.expected.get("icd", []),
            "modifiers": case.expected.get("modifiers", []),
            "added_at": case.created_at.isoformat(),
        }
        for case, service_date, provider_name in rows.tuples()
    ]


async def case_candidates(db: AsyncSession, actor: Actor) -> list[dict[str, Any]]:
    marked = select(EvalCase.note_id).where(EvalCase.practice_id == actor.practice_id)
    rows = await db.execute(
        select(Note, Provider.name)
        .join(Provider, Provider.id == Note.provider_id)
        .where(Note.practice_id == actor.practice_id, Note.status.in_(SETTLED_STATUSES), Note.id.not_in(marked))
        .order_by(Note.approved_at.desc().nulls_last())
        .limit(CANDIDATE_LIMIT)
    )
    candidates = []
    for note, provider_name in list(rows.tuples()):
        final = await latest_codes(db, note.id, "final")
        candidates.append(
            {
                "note_id": note.id,
                "provider_name": provider_name,
                "service_date": note.service_date.isoformat(),
                "codes": [code.label() for code in final],
            }
        )
    return candidates


async def queue_run(db: AsyncSession, actor: Actor) -> dict[str, Any]:
    cases = await db.scalar(select(func.count(EvalCase.id)).where(EvalCase.practice_id == actor.practice_id))
    if not cases:
        raise Conflict("add approved notes to the evaluation set first")
    active = await db.scalar(
        select(EvalRun.id).where(EvalRun.practice_id == actor.practice_id, EvalRun.status.in_(ACTIVE_RUN_STATUSES))
    )
    if active is not None:
        raise Conflict("an evaluation is already queued or running")
    run = EvalRun(
        practice_id=actor.practice_id,
        model=get_settings().gemini_model,
        prompt_version=PROMPT_VERSION,
        status="queued",
        results=[],
        summary={},
        requested_by=actor.user.id,
    )
    db.add(run)
    record_activity(db, actor, "requested evaluation", practice_id=actor.practice_id, detail=f"{cases} cases")
    await db.commit()
    return _run_view(run, None)


async def evaluation_runs(db: AsyncSession, actor: Actor) -> dict[str, Any]:
    runs = await db.scalars(
        select(EvalRun).where(EvalRun.practice_id == actor.practice_id).order_by(EvalRun.created_at, EvalRun.id)
    )
    cases = await db.scalar(select(func.count(EvalCase.id)).where(EvalCase.practice_id == actor.practice_id))
    views: list[dict[str, Any]] = []
    previous: EvalRun | None = None
    for run in runs:
        views.append(_run_view(run, previous))
        if run.status == "done":
            previous = run
    return {"cases": cases or 0, "runs": list(reversed(views))}


async def run_detail(db: AsyncSession, actor: Actor, run_id: str) -> dict[str, Any]:
    run = await db.get(EvalRun, run_id)
    if run is None or run.practice_id != actor.practice_id:
        raise NotFound("evaluation not found")
    previous = await db.scalar(
        select(EvalRun)
        .where(EvalRun.practice_id == run.practice_id, EvalRun.status == "done", EvalRun.created_at < run.created_at)
        .order_by(EvalRun.created_at.desc())
        .limit(1)
    )
    labels = await _case_labels(db, [str(result.get("note_id")) for result in run.results])
    return {
        "run": _run_view(run, previous),
        "results": [{**result, **labels.get(str(result.get("note_id")), {})} for result in run.results],
    }


async def _case_labels(db: AsyncSession, note_ids: list[str]) -> dict[str, dict[str, str]]:
    rows = await db.execute(
        select(Note.id, Note.service_date, Provider.name)
        .join(Provider, Provider.id == Note.provider_id)
        .where(Note.id.in_(note_ids))
    )
    return {
        note_id: {"service_date": service_date.isoformat(), "provider_name": provider_name}
        for note_id, service_date, provider_name in rows.tuples()
    }


def _run_view(run: EvalRun, previous: EvalRun | None) -> dict[str, Any]:
    finished = run.status == "done"
    return {
        "id": run.id,
        "status": run.status,
        "model": run.model,
        "prompt_version": run.prompt_version,
        "requested_at": run.created_at.isoformat() if run.created_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "summary": run.summary,
        "change": run_change(previous.summary if previous else None, run.summary) if finished else None,
    }
