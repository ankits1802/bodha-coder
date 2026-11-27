from __future__ import annotations

from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Query

from app.api.responses.base import ExactRoute
from app.api.responses.expenditure import Expenditure
from app.api.routes.hq import HqActor
from app.core.deps import Db
from app.services import expenditure

router = APIRouter(tags=["hq"], route_class=ExactRoute)


@router.get("/hq/expenditure", response_model=Expenditure)
async def spend(
    db: Db,
    actor: HqActor,
    *,
    start: Annotated[date, Query(alias="from")],
    end: Annotated[date, Query(alias="to")],
    practice_id: str | None = None,
    organization_id: str | None = None,
) -> dict[str, Any]:
    chosen = expenditure.SpendScope(practice_id, organization_id)
    return await expenditure.expenditure(db, start=start, end=end, scope=chosen)
