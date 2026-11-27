from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Actor
from app.core.errors import Conflict
from app.models import AuditSample, Suggestion
from app.services.agreement import summarize
from app.services.audit_log import record_access
from app.services.audit_samples import reference_elements
from app.services.blind_review import reviewer_item
from app.services.samples import sample_id_of

__all__ = ["FEEDBACK_KINDS", "my_training", "training_feedback"]

FEEDBACK_KINDS = ("em", "diagnosis", "modifier", "code_review")


async def my_training(db: AsyncSession, actor: Actor) -> dict[str, Any]:
    rows = list(
        await db.scalars(
            select(AuditSample)
            .where(AuditSample.practice_id == actor.practice_id, AuditSample.reviewer_id == actor.user.id)
            .order_by(AuditSample.created_at.desc())
        )
    )
    groups: dict[str, list[AuditSample]] = defaultdict(list)
    for item in rows:
        groups[sample_id_of(item)].append(item)
    done = [item for item in rows if item.purpose == "training" and item.status == "done"]
    return {
        "sets": [
            {
                "id": sample_id,
                "purpose": items[0].purpose,
                "total": len(items),
                "done": sum(item.status == "done" for item in items),
                "started_at": items[0].result["sample"]["started_at"],
            }
            for sample_id, items in groups.items()
        ],
        "scores": {side: summarize([item.result[side] for item in done]) for side in ("claim", "bodha")},
    }


async def training_feedback(db: AsyncSession, actor: Actor, item_id: str) -> dict[str, Any]:
    item = await reviewer_item(db, actor, item_id)
    if item.purpose != "training" or item.status != "done":
        raise Conflict("feedback opens once the note is coded")
    suggestions = await _suggestions(db, item.analysis_id)
    record_access(db, actor, "opened training feedback", note_id=item.note_id)
    await db.commit()
    return {
        "item_id": item.id,
        "sample_id": sample_id_of(item),
        "answer": {key: item.answer.get(key) for key in ("em", "icd", "modifiers")},
        "bodha": reference_elements(item, "bodha"),
        "claim": reference_elements(item, "claim"),
        "agreement": {"bodha": item.result["bodha"], "claim": item.result["claim"]},
        "suggestions": suggestions,
    }


async def _suggestions(db: AsyncSession, analysis_id: str | None) -> list[dict[str, Any]]:
    if analysis_id is None:
        return []
    rows = await db.scalars(
        select(Suggestion).where(Suggestion.analysis_id == analysis_id, Suggestion.kind.in_(FEEDBACK_KINDS))
    )
    listed = [
        {
            "key": row.key,
            "kind": row.kind,
            "action": row.action,
            "title": row.title,
            "reasoning": row.reasoning,
            "code_before": row.code_before,
            "code_after": row.code_after,
            "evidence": list(row.evidence),
        }
        for row in rows
    ]
    return sorted(listed, key=lambda row: (FEEDBACK_KINDS.index(row["kind"]), row["key"]))
