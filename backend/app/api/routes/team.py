from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.api.bodies import InviteBody, MemberBody
from app.api.wiring import Mail
from app.core.deps import Actor, Db, require
from app.core.roles import ADMINS
from app.services import team

router = APIRouter(prefix="/team", tags=["team"])
Admin = Annotated[Actor, Depends(require(*ADMINS))]


@router.get("")
async def members(db: Db, actor: Admin) -> dict[str, Any]:
    rows = await team.team(db, actor)
    seats = actor.practice.seats if actor.practice else 0
    return {
        "seats": seats,
        "members": [
            {
                "id": u.id,
                "name": u.name,
                "email": u.email,
                "role": u.role,
                "status": u.status,
                "mfa_enabled": u.mfa_enabled,
                "last_active_at": u.last_active_at.isoformat() if u.last_active_at else None,
            }
            for u in rows
        ],
    }


@router.post("")
async def invite(body: InviteBody, db: Db, mail: Mail, actor: Admin) -> dict[str, str]:
    user = await team.invite(db, mail, actor, name=body.name, email=body.email, role=body.role)
    return {"id": user.id}


@router.patch("/{user_id}", status_code=204)
async def update(user_id: str, body: MemberBody, db: Db, actor: Admin) -> None:
    await team.update_member(db, actor, user_id, role=body.role, blocked=body.blocked)


@router.post("/{user_id}/reset-mfa", status_code=204)
async def reset_mfa(user_id: str, db: Db, actor: Admin) -> None:
    await team.reset_mfa(db, actor, user_id)


@router.post("/{user_id}/resend-invite", status_code=204)
async def resend(user_id: str, db: Db, mail: Mail, actor: Admin) -> None:
    await team.resend_invite(db, mail, actor, user_id)
