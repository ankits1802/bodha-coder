from __future__ import annotations

from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, Request, Response

from app.adapters.messenger import Messenger
from app.adapters.seal_keys import RecordSigner
from app.api.bodies import IdentitySignupBody, SignupBody
from app.api.responses.auth import MfaChallenge, SignedIn
from app.api.responses.base import ExactRoute
from app.api.responses.signup import PendingIdentity
from app.api.wiring import (
    Mail,
    Sealer,
    SignupCookie,
    challenge_body,
    clear_signup_cookie,
    client_of,
    signed_in_body,
)
from app.core.db import SessionFactory
from app.core.deps import Db
from app.core.realms import CurrentSite
from app.services import auth, signup


def _signups_here(site: CurrentSite) -> None:
    signup.ensure_signup_here(site)


router = APIRouter(prefix="/signup", tags=["signup"], route_class=ExactRoute, dependencies=[Depends(_signups_here)])


@router.post("", status_code=204)
async def email_signup(
    body: SignupBody, request: Request, db: Db, mail: Mail, background: BackgroundTasks, *, signer: Sealer
) -> None:
    ip, agent = client_of(request)
    form = signup.EmailSignup(body.name, body.practice_name, str(body.email), body.time_zone, body.agreed)
    await signup.check_email_signup(db, form, ip=ip)
    background.add_task(_finish_email_signup, mail, signer, form, signup.Visitor(ip, agent))


async def _finish_email_signup(
    mail: Messenger, signer: RecordSigner, form: signup.EmailSignup, visitor: signup.Visitor
) -> None:
    async with SessionFactory() as db:
        await signup.request_email_signup(db, mail, signer, form, ip=visitor.ip, agent=visitor.agent)


@router.get("/identity", response_model=PendingIdentity)
async def pending_identity(started: SignupCookie = None) -> dict[str, str]:
    identity = signup.pending_identity(started)
    return {"email": identity.email, "name": identity.name, "provider": identity.provider}


@router.post("/identity", response_model=SignedIn | MfaChallenge)
async def identity_signup(
    body: IdentitySignupBody,
    request: Request,
    response: Response,
    db: Db,
    *,
    signer: Sealer,
    started: SignupCookie = None,
) -> dict[str, Any]:
    ip, agent = client_of(request)
    form = signup.IdentitySignup(body.name, body.practice_name, body.time_zone, body.agreed)
    result = await signup.complete_identity_signup(db, signer, started, form, signup.Visitor(ip, agent))
    clear_signup_cookie(response)
    if isinstance(result, auth.MfaChallenge):
        return challenge_body(result)
    return await signed_in_body(db, response, result)
