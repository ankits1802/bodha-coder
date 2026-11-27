from __future__ import annotations

from collections import Counter
from datetime import date, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.calendar import today_in
from app.core.deps import Actor
from app.core.statistics import ChiSquare, chi_square_homogeneity
from app.models import VOIDED, Note, Suggestion
from app.services.agreement import TIMED_LEVEL, em_level

__all__ = ["LEVEL_ORDER", "MIN_NOTES_PER_WINDOW", "PRIOR_DAYS", "RECENT_DAYS", "SHIFT_P_VALUE", "level_mix"]

RECENT_DAYS = 30
PRIOR_DAYS = 90
MIN_NOTES_PER_WINDOW = 30
SHIFT_P_VALUE = 0.05
LEVEL_ORDER = ("Minimal", "Straightforward", "Low", "Moderate", "High", TIMED_LEVEL)


async def level_mix(db: AsyncSession, actor: Actor) -> dict[str, Any]:
    today = today_in(actor.zone)
    recent_start = today - timedelta(days=RECENT_DAYS - 1)
    prior_start = recent_start - timedelta(days=PRIOR_DAYS)
    rows = await db.execute(
        select(Suggestion.code_after, Note.service_date)
        .join(Note, Note.current_analysis_id == Suggestion.analysis_id)
        .where(
            Note.practice_id == actor.practice_id,
            Note.status != VOIDED,
            Suggestion.kind == "em",
            Note.service_date >= prior_start,
            Note.service_date <= today,
        )
    )
    recent, prior = _counts(rows.tuples(), recent_start)
    test = chi_square_homogeneity([recent[level] for level in LEVEL_ORDER], [prior[level] for level in LEVEL_ORDER])
    return {
        "recent": {"start": recent_start.isoformat(), "end": today.isoformat(), "notes": sum(recent.values())},
        "prior": {
            "start": prior_start.isoformat(),
            "end": (recent_start - timedelta(days=1)).isoformat(),
            "notes": sum(prior.values()),
        },
        "levels": [
            {"level": level, "recent": recent[level], "prior": prior[level]}
            for level in LEVEL_ORDER
            if recent[level] or prior[level]
        ],
        "test": _test_view(test),
        "status": _status(recent, prior, test),
    }


def _counts(rows: Any, recent_start: date) -> tuple[Counter[str], Counter[str]]:
    recent: Counter[str] = Counter()
    prior: Counter[str] = Counter()
    for code, service_date in rows:
        level = em_level(code)
        if level is not None:
            (recent if service_date >= recent_start else prior)[level] += 1
    return recent, prior


def _test_view(test: ChiSquare | None) -> dict[str, Any] | None:
    if test is None:
        return None
    return {
        "statistic": test.statistic,
        "degrees_of_freedom": test.degrees_of_freedom,
        "p_value": test.p_value,
    }


def _status(recent: Counter[str], prior: Counter[str], test: ChiSquare | None) -> str:
    if test is None or sum(recent.values()) < MIN_NOTES_PER_WINDOW or sum(prior.values()) < MIN_NOTES_PER_WINDOW:
        return "not_enough"
    return "shifted" if test.p_value < SHIFT_P_VALUE else "steady"
