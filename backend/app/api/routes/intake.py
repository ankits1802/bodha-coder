from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import Field

from app.api.bodies import Body
from app.core.deps import Actor, Db, require
from app.core.roles import ADMINS
from app.models import Practice
from app.services import intake_settings

router = APIRouter(tags=["intake"])
Admin = Annotated[Actor, Depends(require(*ADMINS))]


class IntakeBody(Body):
    enabled: bool
    prefix: str = Field(default=intake_settings.DEFAULT_INBOX, max_length=40)
    provider_by_folder: dict[str, str] = Field(default_factory=dict)
    place_code: str | None = Field(default=None, max_length=2)
    visit_type: str = Field(min_length=1, max_length=40)


@router.get("/practice/intake")
async def intake(db: Db, actor: Admin) -> dict[str, Any]:
    return intake_settings.intake_view(await db.get_one(Practice, actor.practice_id))


@router.put("/practice/intake")
async def save_intake(body: IntakeBody, db: Db, actor: Admin) -> dict[str, Any]:
    return await intake_settings.save_intake(db, actor, body.model_dump())
