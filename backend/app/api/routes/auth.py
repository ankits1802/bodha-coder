from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, Request, Response

from app.adapters.messenger import Messenger
from app.api.bodies import ForgotBody, LoginBody, MfaBody, MfaStartBody, PasswordBody, RecoveryBody
from app.api.responses.auth import MfaChallenge, MfaEnrolment, SignedIn, User
from app.api.responses.base import ExactRoute
from app.api.wiring import Mail, RefreshCookie, clear_refresh_cookie, client_of, set_refresh_cookie, user_view
from app.core.db import SessionFactory
from app.core.deps import Actor, Db, current_actor
from app.core.errors import Unauthorized
from app.models import Practice
from app.services import auth, password_reset

router = APIRouter(prefix="/auth", tags=["auth"], route_class=ExactRoute)


async def _signed_in(db: Db, response: Response, tokens: auth.Tokens) -> dict[str, Any]:
    set_refresh_cookie(response, tokens.refresh)
    practice = await db.get(Practice, tokens.user.practice_id) if tokens.user.practice_id else None
    body: dict[str, Any] = {"access_token": tokens.access, "user": user_view(tokens.user, practice)}
    if tokens.recovery_codes:
        body["recovery_codes"] = list(tokens.recovery_codes)
    return body


@router.post("/login", response_model=SignedIn | MfaChallenge)
async def login(body: LoginBody, request: Request, response: Response, db: Db) -> dict[str, Any]:
    ip, agent = client_of(request)
    result = await auth.login(db, body.email, body.password, ip=ip, agent=agent)
    if isinstance(result, auth.MfaChallenge):
        return {"mfa": result.step, "mfa_token": result.token}
    return await _signed_in(db, response, result)


@router.post("/mfa/setup", response_model=MfaEnrolment)
async def mfa_setup(body: MfaStartBody, db: Db) -> dict[str, str]:
    enrolment = await auth.mfa_enrol(db, body.mfa_token)
    return {"secret": enrolment.secret, "uri": enrolment.uri, "qr_image": enrolment.qr_image}


@router.post("/mfa/verify", response_model=SignedIn)
async def mfa_verify(body: MfaBody, request: Request, response: Response, db: Db) -> dict[str, Any]:
    ip, agent = client_of(request)
    return await _signed_in(db, response, await auth.mfa_verify(db, body.mfa_token, body.code, ip=ip, agent=agent))


@router.post("/mfa/recover", response_model=SignedIn)
async def mfa_recover(body: RecoveryBody, request: Request, response: Response, db: Db) -> dict[str, Any]:
    ip, agent = client_of(request)
    tokens = await auth.mfa_recover(db, body.mfa_token, body.recovery_code, ip=ip, agent=agent)
    return await _signed_in(db, response, tokens)


@router.post("/refresh", response_model=SignedIn)
async def refresh(response: Response, db: Db, refresh_token: RefreshCookie = None) -> dict[str, Any]:
    if not refresh_token:
        raise Unauthorized("sign in again")
    return await _signed_in(db, response, await auth.refresh_session(db, refresh_token))


@router.post("/logout", status_code=204)
async def logout(response: Response, db: Db, refresh_token: RefreshCookie = None) -> None:
    await auth.logout(db, refresh_token)
    clear_refresh_cookie(response)


@router.post("/password", status_code=204)
async def set_password(body: PasswordBody, db: Db) -> None:
    await auth.set_password(db, body.token, body.password)


@router.post("/forgot", status_code=204)
async def forgot(body: ForgotBody, request: Request, db: Db, mail: Mail, background: BackgroundTasks) -> None:
    await password_reset.count_reset_request(db, str(body.email), ip=client_of(request)[0])
    background.add_task(_send_reset, mail, str(body.email))


async def _send_reset(mail: Messenger, email: str) -> None:
    async with SessionFactory() as db:
        await password_reset.send_reset_for_email(db, mail, email)


@router.get("/me", response_model=User)
async def me(actor: Annotated[Actor, Depends(current_actor)]) -> dict[str, Any]:
    return user_view(actor.user, actor.practice)
