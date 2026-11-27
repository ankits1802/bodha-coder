from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, Request, Response

from app.adapters.messenger import Messenger
from app.api.bodies import ForgotBody, LoginBody, MfaBody, MfaStartBody, PasswordBody, RecoveryBody
from app.api.responses.auth import MfaChallenge, MfaEnrolment, SignedIn, User
from app.api.responses.base import ExactRoute
from app.api.wiring import (
    Mail,
    RefreshCookie,
    clear_refresh_cookie,
    client_of,
    sign_in_body,
    signed_in_body,
    user_view,
)
from app.core.db import SessionFactory
from app.core.deps import Actor, Db, PracticeAccess, session_actor
from app.core.errors import Unauthorized
from app.core.realms import CurrentSite
from app.services import auth, password_reset

router = APIRouter(prefix="/auth", tags=["auth"], route_class=ExactRoute)


@router.post("/login", response_model=SignedIn | MfaChallenge)
async def login(body: LoginBody, request: Request, response: Response, db: Db, site: CurrentSite) -> dict[str, Any]:
    result = await auth.login(db, body.email, body.password, realms=site.realms, client=client_of(request))
    return await sign_in_body(db, response, result)


@router.post("/mfa/setup", response_model=MfaEnrolment)
async def mfa_setup(body: MfaStartBody, db: Db, site: CurrentSite) -> dict[str, str]:
    enrolment = await auth.mfa_enrol(db, body.mfa_token, site.realms)
    return {"secret": enrolment.secret, "uri": enrolment.uri, "qr_image": enrolment.qr_image}


@router.post("/mfa/verify", response_model=SignedIn)
async def mfa_verify(body: MfaBody, request: Request, response: Response, db: Db, site: CurrentSite) -> dict[str, Any]:
    tokens = await auth.mfa_verify(db, body.mfa_token, body.code, realms=site.realms, client=client_of(request))
    return await signed_in_body(db, response, tokens)


@router.post("/mfa/recover", response_model=SignedIn)
async def mfa_recover(
    body: RecoveryBody, request: Request, response: Response, db: Db, site: CurrentSite
) -> dict[str, Any]:
    client = client_of(request)
    tokens = await auth.mfa_recover(db, body.mfa_token, body.recovery_code, realms=site.realms, client=client)
    return await signed_in_body(db, response, tokens)


@router.post("/refresh", response_model=SignedIn)
async def refresh(response: Response, db: Db, site: CurrentSite, refresh_token: RefreshCookie = None) -> dict[str, Any]:
    if not refresh_token:
        raise Unauthorized("sign in again")
    return await signed_in_body(db, response, await auth.refresh_session(db, refresh_token, site.realms))


@router.post("/logout", status_code=204)
async def logout(request: Request, response: Response, db: Db, refresh_token: RefreshCookie = None) -> None:
    await auth.logout(db, refresh_token, client=client_of(request))
    clear_refresh_cookie(response)


@router.post("/password", response_model=SignedIn | MfaChallenge)
async def set_password(
    body: PasswordBody, request: Request, response: Response, db: Db, site: CurrentSite
) -> dict[str, Any]:
    result = await auth.set_password(db, body.token, body.password, site.realms, client_of(request))
    return await sign_in_body(db, response, result)


@router.post("/forgot", status_code=204)
async def forgot(
    body: ForgotBody, request: Request, db: Db, mail: Mail, background: BackgroundTasks, *, site: CurrentSite
) -> None:
    await password_reset.count_reset_request(db, str(body.email), ip=client_of(request).ip)
    background.add_task(_send_reset, mail, str(body.email), site.realms)


async def _send_reset(mail: Messenger, email: str, realms: tuple[str, ...]) -> None:
    async with SessionFactory() as db:
        await password_reset.send_reset_for_email(db, mail, email, realms)


@router.get("/me", response_model=User)
async def me(db: Db, actor: Annotated[Actor, Depends(session_actor)]) -> dict[str, Any]:
    return await user_view(db, actor.user, PracticeAccess(actor.practice, actor.membership))
