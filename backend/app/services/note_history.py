from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Analysis, CodeSet, Decision, Provider, User
from app.services.attestations import attestation_view, note_attestations
from app.services.claim_exports import export_view, note_exports
from app.services.claim_snapshots import note_snapshots, snapshot_view
from app.services.pointer_decisions import read_pointer_key

__all__ = ["note_history"]


async def note_history(db: AsyncSession, note_id: str, practice_id: str) -> dict[str, list[dict[str, Any]]]:
    names = dict((await db.execute(select(User.id, User.name).where(User.practice_id == practice_id))).all())
    analyses = await db.scalars(select(Analysis).where(Analysis.note_id == note_id).order_by(Analysis.revision))
    code_sets = await db.scalars(select(CodeSet).where(CodeSet.note_id == note_id).order_by(CodeSet.created_at))
    decisions = await db.scalars(select(Decision).where(Decision.note_id == note_id).order_by(Decision.created_at))
    return {
        "analyses": [_analysis(row) for row in analyses],
        "code_sets": [_code_set(row, names) for row in code_sets],
        "decisions": [_decision(row, names) for row in decisions],
        "snapshots": [snapshot_view(row) for row in await note_snapshots(db, note_id)],
        "exports": [
            {**export_view(export), "snapshot_revision": item.snapshot_revision}
            for export, item in await note_exports(db, note_id)
        ],
        "attestations": await _attestations(db, note_id),
    }


def _analysis(row: Analysis) -> dict[str, Any]:
    return {
        "revision": row.revision,
        "reason": row.reason,
        "status": row.status,
        "model": row.model,
        "finished_at": row.finished_at.isoformat() if row.finished_at else None,
        "error": row.error,
    }


def _code_set(row: CodeSet, names: Mapping[str, str]) -> dict[str, Any]:
    return {
        "kind": row.kind,
        "revision": row.revision,
        "codes": row.codes,
        "reason": row.reason,
        "by": names.get(row.actor_id or ""),
        "role": row.actor_role,
        "at": row.created_at.isoformat(),
        "override_reason": row.override_reason,
        "override_note": row.override_note,
    }


def _decision(row: Decision, names: Mapping[str, str]) -> dict[str, Any]:
    parsed = read_pointer_key(row.suggestion_key)
    return {
        "key": row.suggestion_key,
        "choice": row.choice,
        "by": names.get(row.actor_id),
        "role": row.actor_role,
        "at": row.created_at.isoformat(),
        "pointers": {"code": parsed[0], "diagnoses": list(parsed[1])} if parsed else None,
        "override_reason": row.override_reason,
        "override_note": row.override_note,
    }


async def _attestations(db: AsyncSession, note_id: str) -> list[dict[str, Any]]:
    rows = await note_attestations(db, note_id)
    providers = {row.provider_id for row in rows}
    names = dict((await db.execute(select(Provider.id, Provider.name).where(Provider.id.in_(providers)))).all())
    return [attestation_view(row, names.get(row.provider_id, "")) for row in rows]
