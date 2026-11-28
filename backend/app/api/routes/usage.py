from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.api.responses.base import ExactRoute
from app.api.responses.usage import HqUsageFigures, UsageFigures
from app.api.routes.billing import INSIGHT_PERIODS
from app.api.usage_bodies import UsageBatchBody
from app.core.deps import Actor, Db, require
from app.core.errors import Invalid
from app.core.roles import ADMINS, HQ, PRACTICE_ROLES
from app.services import usage, usage_figures

router = APIRouter(tags=["usage"], route_class=ExactRoute)
DEFAULT_DAYS = 14


def _period(days: int) -> int:
    if days not in INSIGHT_PERIODS:
        raise Invalid(f"days must be one of {', '.join(str(period) for period in INSIGHT_PERIODS)}")
    return days


@router.post("/usage/events", status_code=204)
async def record_events(
    body: UsageBatchBody, db: Db, actor: Annotated[Actor, Depends(require(*PRACTICE_ROLES))]
) -> None:
    records = [usage.UsageRecord(**{**event.model_dump(), "event_id": str(event.event_id)}) for event in body.events]
    await usage.record_usage(db, actor, records)


@router.get("/insights/usage", response_model=UsageFigures)
async def practice_figures(
    db: Db, actor: Annotated[Actor, Depends(require(*ADMINS))], days: int = DEFAULT_DAYS
) -> dict[str, Any]:
    return await usage_figures.practice_usage(db, actor.practice_id, days=_period(days))


@router.get("/hq/usage", response_model=HqUsageFigures)
async def hq_figures(
    db: Db, actor: Annotated[Actor, Depends(require(*HQ))], days: int = DEFAULT_DAYS
) -> dict[str, Any]:
    return await usage_figures.hq_usage(db, days=_period(days))
