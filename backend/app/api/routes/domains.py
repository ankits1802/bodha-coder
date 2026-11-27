from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request

from app.api.organization_bodies import DomainBody, DomainEmailBody, DomainJoinBody, DomainLinkBody, JoinApprovalBody
from app.api.responses.base import Created, ExactRoute
from app.api.responses.organizations import DomainClaimView, JoinRequestRow, VerifiedDomain
from app.api.routes.organizations import OrganizationAdmin
from app.api.wiring import Mail, Resolver, client_of
from app.core.deps import Actor, Db, require
from app.core.errors import Invalid
from app.core.roles import ADMINS
from app.services import domain_claims, join_requests, organizations
from app.services.domain_claims import ClaimScope

router = APIRouter(tags=["domains"], route_class=ExactRoute)
Admin = Annotated[Actor, Depends(require(*ADMINS))]
PRACTICE_DOMAINS = "/practice/domains"
ORGANIZATION_DOMAINS = "/organizations/{organization_id}/domains"


def _practice_scope(actor: Actor) -> ClaimScope:
    return ClaimScope(actor.practice_id, None)


def _organization_scope(organization_id: str) -> ClaimScope:
    return ClaimScope(None, organization_id)


@router.get(PRACTICE_DOMAINS, response_model=list[DomainClaimView])
async def practice_domains(db: Db, actor: Admin) -> list[dict[str, Any]]:
    return await domain_claims.claims_in(db, _practice_scope(actor))


@router.post(PRACTICE_DOMAINS, response_model=Created)
async def claim_for_practice(body: DomainBody, db: Db, actor: Admin) -> dict[str, str]:
    if body.practice_id not in (None, actor.practice_id):
        raise Invalid("claim a domain for this practice")
    claim = await domain_claims.claim_domain(db, actor, _practice_scope(actor), actor.own_practice, body.domain)
    return {"id": claim.id}


@router.post(f"{PRACTICE_DOMAINS}/{{claim_id}}/check", status_code=204)
async def check_practice_domain(claim_id: str, db: Db, actor: Admin, resolver: Resolver) -> None:
    await domain_claims.verify_by_dns(db, resolver, actor, _practice_scope(actor), claim_id)


@router.post(f"{PRACTICE_DOMAINS}/{{claim_id}}/email", status_code=204)
async def email_practice_domain(claim_id: str, body: DomainEmailBody, db: Db, mail: Mail, actor: Admin) -> None:
    scope = _practice_scope(actor)
    await domain_claims.send_verification_email(db, mail, actor, scope, claim_id, mailbox=body.mailbox)


@router.put(f"{PRACTICE_DOMAINS}/{{claim_id}}/join", status_code=204)
async def join_for_practice(claim_id: str, body: DomainJoinBody, db: Db, actor: Admin) -> None:
    scope = _practice_scope(actor)
    await domain_claims.change_join(db, actor, scope, claim_id, mode=body.mode, role=body.role)


@router.delete(f"{PRACTICE_DOMAINS}/{{claim_id}}", status_code=204)
async def release_practice_domain(claim_id: str, db: Db, actor: Admin) -> None:
    await domain_claims.release_claim(db, actor, _practice_scope(actor), claim_id)


@router.get(ORGANIZATION_DOMAINS, response_model=list[DomainClaimView])
async def organization_domains(db: Db, session: OrganizationAdmin) -> list[dict[str, Any]]:
    return await domain_claims.claims_in(db, _organization_scope(session.organization.id))


@router.post(ORGANIZATION_DOMAINS, response_model=Created)
async def claim_for_organization(body: DomainBody, db: Db, session: OrganizationAdmin) -> dict[str, str]:
    if body.practice_id is None:
        raise Invalid("choose the practice people join")
    practice = await organizations.organization_practice(db, session.organization, body.practice_id)
    scope = _organization_scope(session.organization.id)
    claim = await domain_claims.claim_domain(db, session.actor, scope, practice, body.domain)
    return {"id": claim.id}


@router.post(f"{ORGANIZATION_DOMAINS}/{{claim_id}}/check", status_code=204)
async def check_organization_domain(claim_id: str, db: Db, session: OrganizationAdmin, resolver: Resolver) -> None:
    scope = _organization_scope(session.organization.id)
    await domain_claims.verify_by_dns(db, resolver, session.actor, scope, claim_id)


@router.post(f"{ORGANIZATION_DOMAINS}/{{claim_id}}/email", status_code=204)
async def email_organization_domain(
    claim_id: str, body: DomainEmailBody, db: Db, mail: Mail, session: OrganizationAdmin
) -> None:
    scope = _organization_scope(session.organization.id)
    await domain_claims.send_verification_email(db, mail, session.actor, scope, claim_id, mailbox=body.mailbox)


@router.put(f"{ORGANIZATION_DOMAINS}/{{claim_id}}/join", status_code=204)
async def join_for_organization(claim_id: str, body: DomainJoinBody, db: Db, session: OrganizationAdmin) -> None:
    scope = _organization_scope(session.organization.id)
    await domain_claims.change_join(db, session.actor, scope, claim_id, mode=body.mode, role=body.role)


@router.delete(f"{ORGANIZATION_DOMAINS}/{{claim_id}}", status_code=204)
async def release_organization_domain(claim_id: str, db: Db, session: OrganizationAdmin) -> None:
    await domain_claims.release_claim(db, session.actor, _organization_scope(session.organization.id), claim_id)


@router.post("/domain-verifications", response_model=VerifiedDomain)
async def verify_domain_link(body: DomainLinkBody, request: Request, db: Db) -> dict[str, str]:
    verified = await domain_claims.verify_by_email(db, body.token, client_of(request))
    return {"domain": verified.domain, "practice_name": verified.practice_name}


@router.get("/team/join-requests", response_model=list[JoinRequestRow])
async def join_request_list(db: Db, actor: Admin) -> list[dict[str, Any]]:
    return await join_requests.pending_requests(db, actor)


@router.post("/team/join-requests/{request_id}/approve", response_model=Created)
async def approve_join(request_id: str, body: JoinApprovalBody, db: Db, mail: Mail, actor: Admin) -> dict[str, str]:
    return {"id": await join_requests.approve_request(db, mail, actor, request_id, role=body.role)}


@router.post("/team/join-requests/{request_id}/decline", status_code=204)
async def decline_join(request_id: str, db: Db, actor: Admin) -> None:
    await join_requests.decline_request(db, actor, request_id)
