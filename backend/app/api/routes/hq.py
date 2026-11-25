from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.api.bodies import DemoBody, PlaceBody, PracticeBody, PracticeUpdateBody
from app.api.wiring import Mail
from app.core.deps import Actor, Db, require
from app.core.roles import HQ
from app.models import DemoRequest
from app.services import hq

router = APIRouter(tags=["hq"])
HqActor = Annotated[Actor, Depends(require(*HQ))]


@router.get("/hq/overview")
async def overview(db: Db, actor: HqActor) -> dict[str, Any]:
    return await hq.overview(db)


@router.get("/hq/practices")
async def practices(db: Db, actor: HqActor) -> list[dict[str, Any]]:
    return await hq.practices(db)


@router.post("/hq/practices")
async def add_practice(body: PracticeBody, db: Db, mail: Mail, actor: HqActor) -> dict[str, str]:
    practice = await hq.create_practice(
        db,
        mail,
        actor,
        name=body.name,
        admin_name=body.admin_name,
        admin_email=body.admin_email,
        plan=body.plan,
        seats=body.seats,
        time_zone=body.time_zone,
    )
    return {"id": practice.id}


@router.patch("/hq/practices/{practice_id}", status_code=204)
async def edit_practice(practice_id: str, body: PracticeUpdateBody, db: Db, actor: HqActor) -> None:
    await hq.update_practice(db, actor, practice_id, body.model_dump(exclude_unset=True))


@router.get("/hq/places")
async def places(db: Db, actor: HqActor) -> list[dict[str, Any]]:
    return [{"code": p.code, "name": p.name, "active": p.active} for p in await hq.places(db)]


@router.put("/hq/places/{code}", status_code=204)
async def set_place(code: str, body: PlaceBody, db: Db, actor: HqActor) -> None:
    await hq.set_place(db, actor, code, name=body.name, active=body.active)


@router.get("/hq/activity")
async def activity(db: Db, actor: HqActor, practice_id: str | None = None) -> list[dict[str, Any]]:
    return [
        {
            "at": row.created_at.isoformat(),
            "actor": row.actor_name,
            "action": row.action,
            "practice_id": row.practice_id,
            "detail": row.detail,
        }
        for row in await hq.activity(db, practice_id=practice_id)
    ]


@router.post("/demo-requests", status_code=204)
async def demo_request(body: DemoBody, db: Db) -> None:
    db.add(DemoRequest(name=body.name, email=str(body.email), organization=body.organization, message=body.message))
    await db.commit()
