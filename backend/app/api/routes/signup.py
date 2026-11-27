from __future__ import annotations

from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, Request, Response

from app.adapters.messenger import Messenger
from app.adapters.seal_keys import RecordSigner
from app.api.bodies import IdentitySignupBody, SignupBody
from app.api.organization_bodies import IdentityJoinBody, JoinChoiceBody, JoinTicketBody
from app.api.responses.auth import MfaChallenge, SignedIn
from app.api.responses.base import ExactRoute
from app.api.responses.organizations import JoinOutcome, JoinPage
from app.api.responses.signup import PendingIdentity
from app.api.wiring import Mail, Sealer, SignupCookie, clear_signup_cookie, client_of, sign_in_body
from app.core.db import SessionFactory
from app.core.deps import Client, Db
from app.core.realms import CurrentSite
from app.services import domain_join, signup, signup_join


def _signups_here(site: CurrentSite) -> None:
    signup.ensure_signup_here(site)


router = APIRouter(prefix="/signup", tags=["signup"], route_class=ExactRoute, dependencies=[Depends(_signups_here)])


@router.post("", status_code=204)
async def email_signup(
    body: SignupBody, request: Request, db: Db, mail: Mail, background: BackgroundTasks, *, signer: Sealer
) -> None:
    client = client_of(request)
    form = signup.EmailSignup(body.name, body.practice_name, str(body.email), body.time_zone, body.agreed)
    await signup.check_email_signup(db, form, ip=client.ip)
    background.add_task(_finish_email_signup, mail, signer, form, client)


async def _finish_email_signup(mail: Messenger, signer: RecordSigner, form: signup.EmailSignup, client: Client) -> None:
    async with SessionFactory() as db:
        await signup.request_email_signup(db, mail, signer, form, client)


@router.get("/identity", response_model=PendingIdentity)
async def pending_identity(db: Db, started: SignupCookie = None) -> dict[str, Any]:
    identity = signup.pending_identity(started)
    return {
        "email": identity.email,
        "name": identity.name,
        "provider": identity.provider,
        "has_account": await signup.has_account(db, identity.email),
        "join": domain_join.offer_view(await domain_join.join_offer_for(db, identity.email)),
    }


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
    form = signup.IdentitySignup(body.name, body.practice_name, body.time_zone, body.agreed)
    result = await signup.complete_identity_signup(db, signer, started, form, client_of(request))
    clear_signup_cookie(response)
    return await sign_in_body(db, response, result)


@router.post("/identity/join", response_model=SignedIn | MfaChallenge | JoinOutcome)
async def identity_join(
    body: IdentityJoinBody, request: Request, response: Response, db: Db, started: SignupCookie = None
) -> dict[str, Any]:
    result = await signup_join.complete_identity_join(db, started, name=body.name, client=client_of(request))
    clear_signup_cookie(response)
    if result is None:
        return {"outcome": domain_join.REQUESTED}
    return await sign_in_body(db, response, result)


@router.post("/join/offer", response_model=JoinPage)
async def join_offer(body: JoinTicketBody, db: Db) -> dict[str, Any]:
    return await signup_join.join_page(db, body.token)


@router.post("/join", response_model=JoinOutcome)
async def join(body: JoinChoiceBody, request: Request, db: Db, mail: Mail, *, signer: Sealer) -> dict[str, str]:
    client = client_of(request)
    outcome = await signup_join.complete_email_join(db, mail, signer, body.token, join=body.join, client=client)
    return {"outcome": outcome}
