from __future__ import annotations

import asyncio
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.codes.billing_codes import Code, with_pointers
from app.codes.em import is_em_code
from app.codes.ncci import ncci_tables
from app.core.deps import Actor
from app.models import SNAPSHOT_SCHEMA_VERSION, Analysis, ApprovedClaim, CodeSet, Decision, Note, utcnow
from app.services.claim_pointers import POINTER_LETTERS, resolved_pointers
from app.services.code_sets import next_revision
from app.services.finding import Finding
from app.services.memberships import member_names
from app.services.note_texts import current_texts, note_texts
from app.services.override_reasons import departs_from_bodha

__all__ = [
    "Approver",
    "approver_of",
    "latest_snapshots",
    "note_snapshots",
    "snapshot_codes",
    "snapshot_content",
    "snapshot_view",
    "write_snapshot",
]


@dataclass(frozen=True)
class Approver:
    id: str | None
    name: str
    role: str


@dataclass(frozen=True)
class BilledHistory:
    original: tuple[Code, ...]
    latest: tuple[Code, ...]
    revision: int


def approver_of(actor: Actor) -> Approver:
    return Approver(actor.user.id, actor.user.name, actor.role)


async def write_snapshot(
    db: AsyncSession, note: Note, final_set: CodeSet, approver: Approver, findings: Sequence[Finding]
) -> ApprovedClaim:
    codes = tuple(Code.from_json(item) for item in final_set.codes)
    tables = await asyncio.to_thread(ncci_tables)
    claim = with_pointers(codes, resolved_pointers(tables, codes, note.service_date))
    analysis = await db.get(Analysis, note.current_analysis_id) if note.current_analysis_id else None
    texts = current_texts(await note_texts(db, note.id))
    decisions = await _decision_records(db, note, {finding.key: finding for finding in findings})
    snapshot = ApprovedClaim(
        practice_id=note.practice_id,
        note_id=note.id,
        revision=await next_revision(db, ApprovedClaim, note.id),
        final_code_set_id=final_set.id,
        approved_by=approver.id,
        approver_name=approver.name,
        approver_role=approver.role,
        approved_at=note.approved_at or utcnow(),
        analysis_id=analysis.id if analysis else None,
        model=analysis.model if analysis else None,
        prompt_version=analysis.prompt_version if analysis else None,
        text_revision_ids=[text.id for text in texts],
        document_key=note.file_key,
        document_sha256=note.file_sha256,
        schema_version=SNAPSHOT_SCHEMA_VERSION,
        content=snapshot_content(claim, await _billed_history(db, note.id), decisions),
    )
    db.add(snapshot)
    await db.flush()
    return snapshot


def snapshot_content(claim: tuple[Code, ...], billed: BilledHistory, decisions: list[dict[str, Any]]) -> dict[str, Any]:
    diagnoses = [code.code for code in claim if code.type == "ICD-10"]
    letters = dict(zip(diagnoses, POINTER_LETTERS, strict=False))
    em = next((code for code in claim if code.type == "CPT" and is_em_code(code.code)), None)
    return {
        "codes": [code.as_json() for code in claim],
        "em": _line(em) if em else None,
        "procedures": [
            {**_line(code), "pointers": list(code.pointers), "letters": [letters.get(item) for item in code.pointers]}
            for code in claim
            if code.type == "CPT"
        ],
        "diagnoses": [{"letter": letters.get(code), "code": code} for code in diagnoses],
        "billed": [code.as_json() for code in billed.latest],
        "billed_revision": billed.revision,
        "billed_original": [code.as_json() for code in billed.original],
        "decisions": decisions,
    }


def snapshot_codes(snapshot: ApprovedClaim) -> tuple[Code, ...]:
    return tuple(Code.from_json(item) for item in snapshot.content.get("codes", []))


async def latest_snapshots(db: AsyncSession, note_ids: Sequence[str]) -> dict[str, ApprovedClaim]:
    if not note_ids:
        return {}
    rows = await db.scalars(
        select(ApprovedClaim)
        .where(ApprovedClaim.note_id.in_(note_ids))
        .order_by(ApprovedClaim.note_id, ApprovedClaim.revision.desc())
        .distinct(ApprovedClaim.note_id)
    )
    return {row.note_id: row for row in rows}


async def note_snapshots(db: AsyncSession, note_id: str) -> list[ApprovedClaim]:
    rows = await db.scalars(
        select(ApprovedClaim).where(ApprovedClaim.note_id == note_id).order_by(ApprovedClaim.revision)
    )
    return list(rows.all())


def snapshot_view(row: ApprovedClaim) -> dict[str, Any]:
    content = row.content
    return {
        "id": row.id,
        "revision": row.revision,
        "approved_at": row.approved_at.isoformat(),
        "approver_name": row.approver_name,
        "approver_role": row.approver_role,
        "codes": [Code.from_json(item).label() for item in content.get("codes", [])],
        "billed": [Code.from_json(item).label() for item in content.get("billed", [])],
        "decisions": len(content.get("decisions", [])),
        "analysis_id": row.analysis_id,
        "model": row.model,
        "prompt_version": row.prompt_version,
        "text_revisions": len(row.text_revision_ids),
        "document_sha256": row.document_sha256,
    }


def _line(code: Code) -> dict[str, Any]:
    return {"code": code.code, "modifiers": list(code.modifiers), "units": code.units}


async def _billed_history(db: AsyncSession, note_id: str) -> BilledHistory:
    rows = list(
        (
            await db.scalars(
                select(CodeSet).where(CodeSet.note_id == note_id, CodeSet.kind == "billed").order_by(CodeSet.revision)
            )
        ).all()
    )
    if not rows:
        return BilledHistory((), (), 0)
    original, latest = rows[0], rows[-1]
    return BilledHistory(
        tuple(Code.from_json(item) for item in original.codes),
        tuple(Code.from_json(item) for item in latest.codes),
        latest.revision,
    )


async def _decision_records(db: AsyncSession, note: Note, findings: Mapping[str, Finding]) -> list[dict[str, Any]]:
    names = await member_names(db, note.practice_id)
    rows = await db.scalars(select(Decision).where(Decision.note_id == note.id).order_by(Decision.created_at))
    return [_decision_record(row, findings.get(row.suggestion_key), names) for row in rows]


def _decision_record(row: Decision, finding: Finding | None, names: Mapping[str, str]) -> dict[str, Any]:
    return {
        "key": row.suggestion_key,
        "choice": row.choice,
        "title": finding.title if finding else None,
        "departs": bool(finding and departs_from_bodha(finding, row.choice)),
        "override_reason": row.override_reason,
        "override_note": row.override_note,
        "by": names.get(row.actor_id),
        "role": row.actor_role,
        "at": row.created_at.isoformat(),
        "analysis_id": row.analysis_id,
    }
