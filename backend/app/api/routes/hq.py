from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request

from app.api.bodies import (
    DeletePracticeBody,
    DemoBody,
    HqAdminBody,
    HqInviteBody,
    HqMemberBody,
    PlaceBody,
    PracticeBody,
    PracticeUpdateBody,
    RenewBody,
)
from app.api.responses.base import Created, ExactRoute
from app.api.responses.hq import (
    AdminAppointed,
    AdminLinkSent,
    DemoRequestRow,
    HqActivityPage,
    HqOverview,
    HqPlace,
    HqPractice,
    HqTeamMember,
    Renewal,
)
from app.api.wiring import Mail, Store, client_of
from app.core.deps import Actor, Db, require
from app.core.roles import HQ
from app.models import DemoRequest
from app.services import hq, hq_admins, hq_team, records
from app.services.rate_limits import DEMO_PER_IP, hit

router = APIRouter(tags=["hq"], route_class=ExactRoute)
HqActor = Annotated[Actor, Depends(require(*HQ))]


@router.get("/hq/overview", response_model=HqOverview)
async def overview(db: Db, actor: HqActor) -> dict[str, Any]:
    return await hq.overview(db)


@router.get("/hq/practices", response_model=list[HqPractice])
async def practices(db: Db, actor: HqActor) -> list[dict[str, Any]]:
    return await hq.practices(db)


@router.post("/hq/practices", response_model=Created)
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


@router.delete("/hq/practices/{practice_id}", status_code=204)
async def delete_practice(practice_id: str, body: DeletePracticeBody, db: Db, store: Store, actor: HqActor) -> None:
    await records.delete_practice(db, store, actor, practice_id, confirm_name=body.confirm_name)


@router.post("/hq/practices/{practice_id}/admin-link", response_model=AdminLinkSent)
async def admin_link(practice_id: str, db: Db, mail: Mail, actor: HqActor) -> dict[str, str]:
    return {"sent": await hq.send_admin_link(db, mail, actor, practice_id)}


@router.post("/hq/practices/{practice_id}/admins", response_model=AdminAppointed)
async def appoint_admin(practice_id: str, body: HqAdminBody, db: Db, mail: Mail, actor: HqActor) -> dict[str, str]:
    appointment = hq_admins.Appointment(body.name, str(body.email), body.reason)
    return {"outcome": await hq_admins.appoint_admin(db, mail, actor, practice_id, appointment)}


@router.post("/hq/practices/{practice_id}/renew", response_model=Renewal)
async def renew(practice_id: str, body: RenewBody, db: Db, actor: HqActor) -> dict[str, str | None]:
    until = await hq.renew_practice(db, actor, practice_id, body.until)
    return {"renews_on": until.isoformat() if until else None}


@router.get("/hq/places", response_model=list[HqPlace])
async def places(db: Db, actor: HqActor) -> list[dict[str, Any]]:
    return [{"code": p.code, "name": p.name, "active": p.active} for p in await hq.places(db)]


@router.put("/hq/places/{code}", status_code=204)
async def set_place(code: str, body: PlaceBody, db: Db, actor: HqActor) -> None:
    await hq.set_place(db, actor, code, name=body.name, active=body.active)


@router.get("/hq/activity", response_model=HqActivityPage)
async def activity(
    db: Db,
    actor: HqActor,
    practice_id: str | None = None,
    action: str | None = None,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    page = await hq.activity(db, practice_id=practice_id, action=action, offset=offset)
    return {
        "items": [
            {
                "at": row.created_at.isoformat(),
                "actor": row.actor_name,
                "action": row.action,
                "practice_id": row.practice_id,
                "detail": row.detail,
            }
            for row in page.rows
        ],
        "total": page.total,
        "offset": offset,
        "page_size": hq.ACTIVITY_PAGE,
        "actions": page.actions,
    }


@router.get("/hq/team", response_model=list[HqTeamMember])
async def team(db: Db, actor: HqActor) -> list[dict[str, Any]]:
    return [
        {
            "id": member.id,
            "name": member.name,
            "email": member.email,
            "status": member.status,
            "mfa_enabled": member.mfa_enabled,
            "last_active_at": member.last_active_at.isoformat() if member.last_active_at else None,
        }
        for member in await hq_team.hq_team(db)
    ]


@router.post("/hq/team", response_model=Created)
async def invite(body: HqInviteBody, db: Db, mail: Mail, actor: HqActor) -> dict[str, str]:
    return {"id": (await hq_team.invite_hq_member(db, mail, actor, name=body.name, email=str(body.email))).id}


@router.post("/hq/team/{user_id}/resend-invite", status_code=204)
async def resend_invite(user_id: str, db: Db, mail: Mail, actor: HqActor) -> None:
    await hq_team.resend_hq_invite(db, mail, actor, user_id)


@router.patch("/hq/team/{user_id}", status_code=204)
async def update_member(user_id: str, body: HqMemberBody, db: Db, actor: HqActor) -> None:
    if body.blocked:
        await hq_team.deactivate_hq_member(db, actor, user_id)
    else:
        await hq_team.reactivate_hq_member(db, actor, user_id)


@router.get("/hq/demo-requests", response_model=list[DemoRequestRow])
async def demo_requests(db: Db, actor: HqActor) -> list[dict[str, Any]]:
    return [
        {
            "id": row.id,
            "name": row.name,
            "email": row.email,
            "organization": row.organization,
            "message": row.message,
            "received_at": row.created_at.isoformat(),
        }
        for row in await hq.demo_requests(db)
    ]


@router.post("/demo-requests", status_code=204)
async def demo_request(body: DemoBody, request: Request, db: Db) -> None:
    await hit(db, DEMO_PER_IP, client_of(request).ip)
    db.add(DemoRequest(name=body.name, email=str(body.email), organization=body.organization, message=body.message))
    await db.commit()
