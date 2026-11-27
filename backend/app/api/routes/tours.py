from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.api.bodies import TourBody
from app.api.responses.base import ExactRoute
from app.api.responses.tours import Tour, TourRecord
from app.core.deps import Actor, Db, current_actor
from app.services import tours

router = APIRouter(prefix="/account/tours", tags=["account"], route_class=ExactRoute)
Me = Annotated[Actor, Depends(current_actor)]


@router.get("", response_model=list[TourRecord])
async def tours_taken(db: Db, actor: Me) -> list[dict[str, Any]]:
    return await tours.tours_taken(db, actor.user)


@router.put("/{tour}", response_model=TourRecord)
async def record_tour(tour: Tour, body: TourBody, db: Db, actor: Me) -> dict[str, Any]:
    return await tours.record_tour(db, actor.user, tour, version=body.version, outcome=body.outcome)
