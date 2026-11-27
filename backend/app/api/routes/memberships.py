from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Response

from app.api.bodies import NewPracticeBody, SwitchPracticeBody
from app.api.responses.auth import MfaChallenge, SignedIn
from app.api.responses.base import ExactRoute
from app.api.wiring import RefreshCookie, sign_in_body
from app.core.deps import Actor, Db, session_actor
from app.core.realms import CurrentSite
from app.services import memberships, practice_switch, signup

router = APIRouter(prefix="/auth", tags=["account"], route_class=ExactRoute)
Me = Annotated[Actor, Depends(session_actor)]


@router.post("/practice", response_model=SignedIn | MfaChallenge)
async def switch(
    body: SwitchPracticeBody, response: Response, db: Db, actor: Me, refresh_token: RefreshCookie = None
) -> dict[str, Any]:
    result = await practice_switch.switch_practice(db, actor.user, refresh_token, body.practice_id, client=actor.client)
    return await sign_in_body(db, response, result)


@router.post("/practices", response_model=SignedIn | MfaChallenge)
async def add_practice(
    body: NewPracticeBody,
    response: Response,
    db: Db,
    actor: Me,
    *,
    site: CurrentSite,
    refresh_token: RefreshCookie = None,
) -> dict[str, Any]:
    signup.ensure_signup_here(site)
    form = signup.AnotherPractice(body.practice_name, body.time_zone, body.agreed)
    practice_id = await signup.start_another_practice(db, actor.user, form, actor.client)
    result = await practice_switch.switch_practice(db, actor.user, refresh_token, practice_id, client=actor.client)
    return await sign_in_body(db, response, result)


@router.post("/practices/{practice_id}/leave", status_code=204)
async def leave(practice_id: str, db: Db, actor: Me) -> None:
    await memberships.leave_practice(db, actor.user, practice_id, client=actor.client)
