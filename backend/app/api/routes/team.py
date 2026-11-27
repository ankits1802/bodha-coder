from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.api.bodies import InviteBody, MemberBody
from app.api.responses.base import Created, ExactRoute
from app.api.responses.team import TeamList
from app.api.wiring import Mail
from app.core.deps import Actor, Db, require
from app.core.roles import ADMINS
from app.services import team

router = APIRouter(prefix="/team", tags=["team"], route_class=ExactRoute)
Admin = Annotated[Actor, Depends(require(*ADMINS))]


@router.get("", response_model=TeamList)
async def members(db: Db, actor: Admin) -> dict[str, Any]:
    rows = await team.team(db, actor)
    return {
        "seats": actor.own_practice.seats,
        "members": [
            {
                "id": row.person.id,
                "name": row.person.name,
                "email": row.person.email,
                "role": row.membership.role,
                "status": row.membership.status,
                "mfa_enabled": row.person.mfa_enabled,
                "last_active_at": row.person.last_active_at.isoformat() if row.person.last_active_at else None,
            }
            for row in rows
        ],
    }


@router.post("", response_model=Created)
async def invite(body: InviteBody, db: Db, mail: Mail, actor: Admin) -> dict[str, str]:
    user = await team.invite(db, mail, actor, name=body.name, email=body.email, role=body.role)
    return {"id": user.id}


@router.patch("/{user_id}", status_code=204)
async def update(user_id: str, body: MemberBody, db: Db, actor: Admin) -> None:
    await team.update_member(db, actor, user_id, role=body.role, blocked=body.blocked)


@router.delete("/{user_id}", status_code=204)
async def remove(user_id: str, db: Db, actor: Admin) -> None:
    await team.remove_member(db, actor, user_id)


@router.post("/{user_id}/reset-mfa", status_code=204)
async def reset_mfa(user_id: str, db: Db, actor: Admin) -> None:
    await team.reset_mfa(db, actor, user_id)


@router.post("/{user_id}/resend-invite", status_code=204)
async def resend(user_id: str, db: Db, mail: Mail, actor: Admin) -> None:
    await team.resend_invite(db, mail, actor, user_id)


@router.post("/{user_id}/reset-password", status_code=204)
async def reset_password(user_id: str, db: Db, mail: Mail, actor: Admin) -> None:
    await team.send_password_reset(db, mail, actor, user_id)
