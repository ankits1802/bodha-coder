from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.object_store import ObjectStore
from app.core.config import get_settings
from app.core.deps import Actor
from app.models import AddendumRequest, Analysis, CodeSet, Decision, NoteText, Provider, User
from app.services.audit_log import record_access
from app.services.placement import current_decisions, current_findings
from app.services.review_actions import allowed_choices, current_claim, note_for
from app.services.routing import choices_for
from app.services.worklists import summary


async def note_detail(db: AsyncSession, actor: Actor, note_id: str) -> dict[str, Any]:
    note = await note_for(db, actor, note_id)
    provider = await db.get_one(Provider, note.provider_id)
    findings = await current_findings(db, note)
    choices = choices_for(findings, await current_decisions(db, note.id))
    analysis = await db.get(Analysis, note.current_analysis_id) if note.current_analysis_id else None
    record_access(db, actor, "opened note", note_id=note.id)
    await db.commit()
    return {
        "note": {
            **summary(note, provider.name),
            "patient_age": note.patient_age,
            "patient_sex": note.patient_sex,
            "place_code": note.place_code,
            "visit_type": note.visit_type,
            "flag_reason": note.flag_reason,
            "provider": {
                "id": provider.id,
                "name": provider.name,
                "credential": provider.credential,
                "specialty": provider.specialty,
                "channel": provider.channel,
            },
        },
        "failure": await _latest_failure(db, note.id) if note.status == "failed" else None,
        "texts": await _texts(db, note.id),
        "analysis": _analysis(analysis),
        "findings": [
            {
                **finding.__dict__,
                "evidence": list(finding.evidence),
                "choice": choices[finding.key],
                "allowed": list(allowed_choices(finding)),
            }
            for finding in findings
        ],
        "claim": [code.label() for code in await current_claim(db, note)] if analysis else [],
        "history": await _history(db, note.id, note.practice_id),
        "requests": await _requests(db, note.id),
    }


async def _latest_failure(db: AsyncSession, note_id: str) -> str | None:
    return await db.scalar(
        select(Analysis.error)
        .where(Analysis.note_id == note_id, Analysis.status == "failed")
        .order_by(Analysis.revision.desc())
        .limit(1)
    )


async def _texts(db: AsyncSession, note_id: str) -> list[dict[str, Any]]:
    rows = await db.scalars(select(NoteText).where(NoteText.note_id == note_id).order_by(NoteText.revision))
    return [
        {"revision": row.revision, "source": row.source, "text": row.text, "created_at": row.created_at.isoformat()}
        for row in rows
    ]


def _analysis(analysis: Analysis | None) -> dict[str, Any] | None:
    if analysis is None:
        return None
    report = analysis.report or {}
    return {
        "id": analysis.id,
        "revision": analysis.revision,
        "status": analysis.status,
        "model": analysis.model,
        "prompt_version": analysis.prompt_version,
        "finished_at": analysis.finished_at.isoformat() if analysis.finished_at else None,
        "failed_sections": analysis.context.get("failed_sections", []),
        "cdi": {
            key: (report.get("cdi") or {}).get(key)
            for key in ("overallCDIScore", "summaryGuidance", "codeLinkingOpportunities")
        },
        "audit": {
            key: (report.get("audit") or {}).get(key)
            for key in (
                "overallComplianceScore",
                "auditSummary",
                "requiredElements",
                "codingCompliance",
                "cmsCDICompliance",
            )
        },
        "mips_scope": (report.get("mips") or {}).get("scope"),
    }


async def _history(db: AsyncSession, note_id: str, practice_id: str) -> dict[str, list[dict[str, Any]]]:
    names = dict((await db.execute(select(User.id, User.name).where(User.practice_id == practice_id))).all())
    analyses = await db.scalars(select(Analysis).where(Analysis.note_id == note_id).order_by(Analysis.revision))
    code_sets = await db.scalars(select(CodeSet).where(CodeSet.note_id == note_id).order_by(CodeSet.created_at))
    decisions = await db.scalars(select(Decision).where(Decision.note_id == note_id).order_by(Decision.created_at))
    return {
        "analyses": [
            {
                "revision": a.revision,
                "reason": a.reason,
                "status": a.status,
                "model": a.model,
                "finished_at": a.finished_at.isoformat() if a.finished_at else None,
                "error": a.error,
            }
            for a in analyses
        ],
        "code_sets": [
            {
                "kind": c.kind,
                "revision": c.revision,
                "codes": c.codes,
                "reason": c.reason,
                "by": names.get(c.actor_id or ""),
                "at": c.created_at.isoformat(),
            }
            for c in code_sets
        ],
        "decisions": [
            {"key": d.suggestion_key, "choice": d.choice, "by": names.get(d.actor_id), "at": d.created_at.isoformat()}
            for d in decisions
        ],
    }


async def _requests(db: AsyncSession, note_id: str) -> list[dict[str, Any]]:
    rows = await db.scalars(
        select(AddendumRequest).where(AddendumRequest.note_id == note_id).order_by(AddendumRequest.created_at)
    )
    return [
        {
            "id": r.id,
            "status": r.status,
            "channel": r.channel,
            "questions": r.questions,
            "answers": r.answers,
            "addendum_text": r.addendum_text,
            "hold_claim": r.hold_claim,
            "sent_at": r.created_at.isoformat(),
            "answered_at": r.answered_at.isoformat() if r.answered_at else None,
        }
        for r in rows
    ]


async def pdf_link(db: AsyncSession, store: ObjectStore, actor: Actor, note_id: str) -> str:
    note = await note_for(db, actor, note_id)
    record_access(db, actor, "opened PDF", note_id=note.id)
    await db.commit()
    return await store.signed_url(note.file_key, seconds=get_settings().pdf_link_seconds)
