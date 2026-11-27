from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CLOSED_STATUSES, Organization, Practice
from app.services.insights import insights
from app.services.organizations import organization_practices

__all__ = ["OUTCOME_KEYS", "organization_insights"]

OUTCOME_KEYS = ("matched", "billed_too_low", "billed_too_high", "diagnosis_changes")
COUNTED = ("notes", "approved", "approved_on_time", "estimated_notes")


async def organization_insights(db: AsyncSession, organization: Organization, *, days: int) -> dict[str, Any]:
    practices = [
        practice
        for practice in await organization_practices(db, organization.id)
        if practice.status not in CLOSED_STATUSES
    ]
    rows = [await _practice_figures(db, practice, days) for practice in practices]
    return {"days": days, "totals": _totals(rows), "practices": rows}


async def _practice_figures(db: AsyncSession, practice: Practice, days: int) -> dict[str, Any]:
    found = await insights(db, practice.id, days=days, time_zone=practice.time_zone)
    return {
        "id": practice.id,
        "name": practice.name,
        "notes": sum(day["notes"] for day in found["per_day"]),
        "approved": found["approved"],
        "approved_on_time": found["approved_on_time"],
        "outcomes": dict(found["outcomes"]),
        "estimated_notes": found["estimates"]["notes"],
        "difference": found["estimates"]["difference"],
    }


def _totals(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        **{key: sum(row[key] for row in rows) for key in COUNTED},
        "outcomes": {key: sum(row["outcomes"][key] for row in rows) for key in OUTCOME_KEYS},
        "difference": round(sum(row["difference"] for row in rows), 2),
    }
