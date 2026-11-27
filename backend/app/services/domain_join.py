from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.messenger import Messenger
from app.core.config import get_settings
from app.core.deps import ACTIVE_PRACTICE_STATUSES
from app.core.errors import Conflict, Unauthorized
from app.core.security import TokenError, issue_token, read_token
from app.models import DomainClaim, DomainJoinRequest, Practice, PracticeMembership, User
from app.services.audit_log import SystemActor, record_system_access
from app.services.email_domains import domain_of, is_public_domain
from app.services.inbox import Notice, notify_admins
from app.services.memberships import enrol, membership_in
from app.services.plan_limits import ensure_user_room

__all__ = [
    "AUTO",
    "JOINED",
    "JOIN_TOKEN",
    "REQUESTED",
    "JoinOffer",
    "JoinTicket",
    "admit_by_domain",
    "join_offer_for",
    "join_ticket",
    "offer_view",
    "read_join_ticket",
    "request_by_domain",
    "room_for",
    "send_join_offer",
]

AUTO, REQUEST = "auto", "request"
JOINED, REQUESTED, PENDING = "joined", "requested", "pending"
JOIN_TOKEN = "domain_join"
JOIN_LINK_MINUTES = 72 * 60
JOIN_REQUESTED_KIND = "join_requested"
DOMAIN_JOIN = SystemActor("bodha-domain-join", "Bodha (email domain)")
JOINED_BY_DOMAIN = "joined by email domain"
JOIN_REQUESTED = "join requested"
ALREADY_MEMBER = "you are already on the team of this practice"
START_AGAIN = "this link has expired; start sign-up again"


@dataclass(frozen=True)
class JoinOffer:
    claim_id: str
    domain: str
    practice_id: str
    practice_name: str
    mode: str
    role: str


@dataclass(frozen=True)
class JoinTicket:
    email: str
    name: str
    practice_name: str
    time_zone: str


def offer_view(offer: JoinOffer | None) -> dict[str, Any] | None:
    return None if offer is None else {"practice_name": offer.practice_name, "mode": offer.mode}


async def join_offer_for(db: AsyncSession, email: str) -> JoinOffer | None:
    domain = domain_of(email)
    if domain is None or is_public_domain(domain):
        return None
    found = await db.execute(
        select(DomainClaim, Practice)
        .join(Practice, Practice.id == DomainClaim.practice_id)
        .where(
            DomainClaim.domain == domain,
            DomainClaim.verified_at.is_not(None),
            DomainClaim.released_at.is_(None),
            DomainClaim.join_mode.in_((AUTO, REQUEST)),
            Practice.status.in_(ACTIVE_PRACTICE_STATUSES),
        )
    )
    row = found.tuples().first()
    if row is None:
        return None
    claim, practice = row
    return JoinOffer(claim.id, claim.domain, practice.id, practice.name, claim.join_mode, claim.join_role)


async def room_for(db: AsyncSession, practice_id: str) -> bool:
    practice = await db.get_one(Practice, practice_id)
    try:
        await ensure_user_room(db, practice)
    except Conflict:
        return False
    return True


async def admit_by_domain(db: AsyncSession, offer: JoinOffer, person: User) -> PracticeMembership:
    current = await membership_in(db, person.id, offer.practice_id)
    if current is not None and current.ended_at is None:
        raise Conflict(ALREADY_MEMBER)
    membership = await enrol(db, person, offer.practice_id, offer.role, invited_by=None)
    db.add(
        DomainJoinRequest(
            claim_id=offer.claim_id,
            practice_id=offer.practice_id,
            email=person.email,
            name=person.name,
            status=JOINED,
            role=offer.role,
            user_id=person.id,
        )
    )
    detail = f"{person.name} as {offer.role}, {offer.domain}"
    record_system_access(db, DOMAIN_JOIN, offer.practice_id, JOINED_BY_DOMAIN, detail=detail)
    return membership


async def request_by_domain(db: AsyncSession, offer: JoinOffer, *, name: str, email: str) -> DomainJoinRequest:
    address = email.strip().lower()
    waiting = await db.scalar(
        select(DomainJoinRequest).where(
            DomainJoinRequest.practice_id == offer.practice_id,
            DomainJoinRequest.email == address,
            DomainJoinRequest.status == PENDING,
        )
    )
    if waiting is not None:
        return waiting
    request = DomainJoinRequest(
        claim_id=offer.claim_id, practice_id=offer.practice_id, email=address, name=name.strip(), status=PENDING
    )
    db.add(request)
    await db.flush()
    record_system_access(db, DOMAIN_JOIN, offer.practice_id, JOIN_REQUESTED, detail=f"{request.name}, {offer.domain}")
    notice = Notice(JOIN_REQUESTED_KIND, actor_name=request.name, payload={"request_id": request.id})
    await notify_admins(db, offer.practice_id, notice)
    return request


def join_ticket(ticket: JoinTicket) -> str:
    claims = {"name": ticket.name, "own": ticket.practice_name, "zone": ticket.time_zone}
    return issue_token(JOIN_TOKEN, ticket.email, JOIN_LINK_MINUTES, **claims)


def read_join_ticket(token: str) -> JoinTicket:
    try:
        claims = read_token(token, JOIN_TOKEN)
    except TokenError as error:
        raise Unauthorized(START_AGAIN) from error
    return JoinTicket(str(claims["sub"]), str(claims["name"]), str(claims["own"]), str(claims["zone"]))


async def send_join_offer(messenger: Messenger, ticket: JoinTicket, offer: JoinOffer) -> None:
    link = f"{get_settings().app_url}/sign-up/join#{join_ticket(ticket)}"
    verb = "join" if offer.mode == AUTO else "ask to join"
    await messenger.email(
        ticket.email,
        subject=f"Join {offer.practice_name} on Bodha Assure",
        body=(
            f"{ticket.name}, people at {offer.domain} use Bodha Assure as {offer.practice_name}. "
            f"You can {verb} {offer.practice_name}, or start {ticket.practice_name} as its own practice: {link}. "
            "If this was not you, you can ignore this email."
        ),
    )
