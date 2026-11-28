from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.object_store import ObjectStore
from app.core.config import get_settings
from app.core.deps import Actor
from app.models import AddendumRequest, Analysis, Decision, Note, NoteText, Provider, User
from app.services.audit_log import record_access
from app.services.code_sets import latest_codes
from app.services.estimates import note_estimate
from app.services.finding import Finding
from app.services.finding_impacts import ClaimContext, amount_changes
from app.services.note_history import note_history
from app.services.note_returns import open_return, return_records, undecided_items
from app.services.note_texts import current_texts
from app.services.override_reasons import departing_choices, departs_from_bodha
from app.services.payers import payer_changed
from app.services.placement import current_findings
from app.services.review_actions import allowed_choices, current_claim, note_for
from app.services.routing import choices_for
from app.services.worklists import assignee_name, summary

PROVIDER_FIELDS = ("id", "name", "credential", "specialty", "channel")


@dataclass(frozen=True)
class FindingMarks:
    latest: Mapping[str, Decision]
    again: set[str]
    amounts: Mapping[str, float | None]


async def note_detail(db: AsyncSession, actor: Actor, note_id: str) -> dict[str, Any]:
    note = await note_for(db, actor, note_id)
    provider = await db.get_one(Provider, note.provider_id)
    findings = await current_findings(db, note)
    latest = await _latest_decisions(db, note.id)
    choices = choices_for(findings, {key: row.choice for key, row in latest.items()})
    analysis = await db.get(Analysis, note.current_analysis_id) if note.current_analysis_id else None
    claim = await current_claim(db, note) if analysis else ()
    record_access(db, actor, "opened note", note_id=note.id)
    await db.commit()
    marks = FindingMarks(
        latest=latest,
        again=set(await undecided_items(db, note, findings)),
        amounts=amount_changes(await _claim_context(db, note, findings, choices)),
    )
    return {
        "note": await _header(db, note, provider),
        "failure": await _latest_failure(db, note.id) if note.status == "failed" else None,
        "texts": await _texts(db, note.id),
        "analysis": _analysis(analysis, changed=payer_changed(actor.practice, note, analysis)),
        "findings": [_finding(finding, choices[finding.key], marks) for finding in findings],
        "claim": [code.label() for code in claim],
        "estimate": await note_estimate(db, note, claim) if analysis else None,
        "history": {**await note_history(db, note.id, note.practice_id), "returns": await return_records(db, note.id)},
        "requests": await _requests(db, note.id),
    }


async def _header(db: AsyncSession, note: Note, provider: Provider) -> dict[str, Any]:
    return {
        **summary(note, provider.name),
        "assignee_name": await assignee_name(db, note),
        "patient_age": note.patient_age,
        "patient_sex": note.patient_sex,
        "provider": {key: getattr(provider, key) for key in PROVIDER_FIELDS},
        "voided": await _voided(db, note),
        "returned": await _returned(db, note),
    }


async def _claim_context(
    db: AsyncSession, note: Note, findings: list[Finding], choices: Mapping[str, str]
) -> ClaimContext:
    billed = await latest_codes(db, note.id, "billed")
    return ClaimContext(billed, findings, choices, note.place_code, note.service_date)


async def _returned(db: AsyncSession, note: Note) -> dict[str, Any] | None:
    opened = await open_return(db, note)
    if opened is None:
        return None
    by = await db.scalar(select(User.name).where(User.id == opened.actor_id))
    return {
        "reason": opened.reason,
        "note": opened.note,
        "by": by,
        "at": opened.created_at.isoformat(),
        "items": len(opened.finding_keys),
    }


async def _latest_decisions(db: AsyncSession, note_id: str) -> dict[str, Decision]:
    rows = await db.scalars(select(Decision).where(Decision.note_id == note_id).order_by(Decision.created_at))
    return {row.suggestion_key: row for row in rows}


def _finding(finding: Finding, choice: str, marks: FindingMarks) -> dict[str, Any]:
    allowed = allowed_choices(finding)
    decided = marks.latest.get(finding.key)
    reasoned = decided is not None and decided.override_reason is not None
    return {
        **finding.__dict__,
        "evidence": list(finding.evidence),
        "choice": choice,
        "allowed": list(allowed),
        "departing_choices": departing_choices(finding, allowed),
        "override": {"reason": decided.override_reason, "note": decided.override_note} if reasoned else None,
        "override_needed": decided is not None and not reasoned and departs_from_bodha(finding, decided.choice),
        "decided": decided is not None,
        "decide_again": finding.key in marks.again,
        "amount_change": marks.amounts.get(finding.key),
    }


async def _voided(db: AsyncSession, note: Note) -> dict[str, Any] | None:
    if note.voided_at is None:
        return None
    by = await db.scalar(select(User.name).where(User.id == note.voided_by)) if note.voided_by else None
    return {"at": note.voided_at.isoformat(), "by": by, "reason": note.void_reason, "was": note.status_before_void}


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
        for row in current_texts(rows.all())
        if row.text
    ]


def _analysis(analysis: Analysis | None, *, changed: bool) -> dict[str, Any] | None:
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
        "payer_changed": changed,
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
            "purpose": r.purpose,
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
