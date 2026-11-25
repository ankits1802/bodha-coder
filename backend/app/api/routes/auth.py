from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Cookie, Depends, Request, Response

from app.api.bodies import LoginBody, MfaBody, MfaStartBody, PasswordBody
from app.api.wiring import REFRESH_COOKIE, clear_refresh_cookie, set_refresh_cookie, user_view
from app.core.deps import Actor, Db, current_actor
from app.core.errors import Unauthorized
from app.models import Practice
from app.services import auth

router = APIRouter(prefix="/auth", tags=["auth"])


def _client(request: Request) -> tuple[str | None, str | None]:
    return (request.client.host if request.client else None), request.headers.get("user-agent")


async def _signed_in(db: Db, response: Response, tokens: auth.Tokens) -> dict[str, Any]:
    set_refresh_cookie(response, tokens.refresh)
    practice = await db.get(Practice, tokens.user.practice_id) if tokens.user.practice_id else None
    return {"access_token": tokens.access, "user": user_view(tokens.user, practice)}


@router.post("/login")
async def login(body: LoginBody, request: Request, response: Response, db: Db) -> dict[str, Any]:
    ip, agent = _client(request)
    result = await auth.login(db, body.email, body.password, ip=ip, agent=agent)
    if isinstance(result, auth.MfaChallenge):
        return {"mfa": result.step, "mfa_token": result.token}
    return await _signed_in(db, response, result)


@router.post("/mfa/setup")
async def mfa_setup(body: MfaStartBody, db: Db) -> dict[str, str]:
    enrolment = await auth.mfa_enrol(db, body.mfa_token)
    return {"secret": enrolment.secret, "uri": enrolment.uri, "qr_image": enrolment.qr_image}


@router.post("/mfa/verify")
async def mfa_verify(body: MfaBody, request: Request, response: Response, db: Db) -> dict[str, Any]:
    ip, agent = _client(request)
    return await _signed_in(db, response, await auth.mfa_verify(db, body.mfa_token, body.code, ip=ip, agent=agent))


@router.post("/refresh")
async def refresh(
    response: Response, db: Db, refresh_token: Annotated[str | None, Cookie(alias=REFRESH_COOKIE)] = None
) -> dict[str, Any]:
    if not refresh_token:
        raise Unauthorized("sign in again")
    return await _signed_in(db, response, await auth.refresh_session(db, refresh_token))


@router.post("/logout", status_code=204)
async def logout(
    response: Response, db: Db, refresh_token: Annotated[str | None, Cookie(alias=REFRESH_COOKIE)] = None
) -> None:
    await auth.logout(db, refresh_token)
    clear_refresh_cookie(response)


@router.post("/password", status_code=204)
async def set_password(body: PasswordBody, db: Db) -> None:
    await auth.set_password(db, body.token, body.password)


@router.get("/me")
async def me(actor: Annotated[Actor, Depends(current_actor)]) -> dict[str, Any]:
    return user_view(actor.user, actor.practice)
