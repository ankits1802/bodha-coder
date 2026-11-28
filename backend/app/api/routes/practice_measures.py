from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.api.measure_bodies import PracticeMeasureBody, PracticeMeasureChangeBody, PracticeMeasureRetireBody
from app.api.responses.base import ExactRoute
from app.api.responses.practice import PracticeMeasureView
from app.core.deps import Actor, Db, require
from app.core.roles import ADMINS
from app.services import practice_measures

router = APIRouter(prefix="/mips/practice-measures", tags=["practice"], route_class=ExactRoute)
Admin = Annotated[Actor, Depends(require(*ADMINS))]


@router.post("", response_model=PracticeMeasureView)
async def add_measure(body: PracticeMeasureBody, db: Db, actor: Admin) -> dict[str, Any]:
    values = practice_measures.checked_values(body.model_dump())
    return practice_measures.measure_view(await practice_measures.add_measure(db, actor, values))


@router.put("/{measure_key}", response_model=PracticeMeasureView)
async def change_measure(measure_key: str, body: PracticeMeasureChangeBody, db: Db, actor: Admin) -> dict[str, Any]:
    values = practice_measures.checked_values(body.model_dump(exclude={"expected_version"}))
    row = await practice_measures.change_measure(db, actor, measure_key, values, expected_version=body.expected_version)
    return practice_measures.measure_view(row)


@router.post("/{measure_key}/retire", status_code=204)
async def retire_measure(measure_key: str, body: PracticeMeasureRetireBody, db: Db, actor: Admin) -> None:
    await practice_measures.retire_measure(db, actor, measure_key, expected_version=body.expected_version)
