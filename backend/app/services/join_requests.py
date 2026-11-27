from __future__ import annotations

from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.messenger import Messenger
from app.core.deps import Actor
from app.core.errors import Forbidden, NotFound
from app.core.roles import INVITABLE_ROLES
from app.models import DomainClaim, DomainJoinRequest, InboxItem, utcnow
from app.services.audit_log import record_access
from app.services.team import Newcomer, bring_in

__all__ = ["JOIN_APPROVED", "JOIN_DECLINED", "approve_request", "decline_request", "pending_requests"]

JOIN_APPROVED = "join request approved"
JOIN_DECLINED = "join request declined"
PENDING, APPROVED, DECLINED = "pending", "approved", "declined"
JOIN_REQUESTED_KIND = "join_requested"


async def pending_requests(db: AsyncSession, actor: Actor) -> list[dict[str, Any]]:
    rows = await db.execute(
        select(DomainJoinRequest, DomainClaim.domain, DomainClaim.join_role)
        .join(DomainClaim, DomainClaim.id == DomainJoinRequest.claim_id)
        .where(DomainJoinRequest.practice_id == actor.practice_id, DomainJoinRequest.status == PENDING)
        .order_by(DomainJoinRequest.created_at, DomainJoinRequest.id)
    )
    return [
        {
            "id": request.id,
            "name": request.name,
            "email": request.email,
            "domain": domain,
            "suggested_role": role,
            "created_at": request.created_at.isoformat(),
        }
        for request, domain, role in rows.tuples()
    ]


async def approve_request(db: AsyncSession, messenger: Messenger, actor: Actor, request_id: str, *, role: str) -> str:
    if role not in INVITABLE_ROLES:
        raise Forbidden("that role cannot be given")
    request = await _pending(db, actor, request_id)
    newcomer = Newcomer(request.name, request.email, role)
    arrival = await bring_in(db, messenger, actor.own_practice, newcomer, by=actor.user)
    request.status, request.role, request.user_id = APPROVED, role, arrival.person.id
    request.decided_by, request.decided_at = actor.user.id, utcnow()
    record_access(db, actor, JOIN_APPROVED, detail=f"{request.name} as {role}")
    await _settle_notices(db, actor, request.id)
    await db.commit()
    return arrival.person.id


async def decline_request(db: AsyncSession, actor: Actor, request_id: str) -> None:
    request = await _pending(db, actor, request_id)
    request.status, request.decided_by, request.decided_at = DECLINED, actor.user.id, utcnow()
    record_access(db, actor, JOIN_DECLINED, detail=request.name)
    await _settle_notices(db, actor, request.id)
    await db.commit()


async def _pending(db: AsyncSession, actor: Actor, request_id: str) -> DomainJoinRequest:
    request = await db.get(DomainJoinRequest, request_id, with_for_update=True)
    if request is None or request.practice_id != actor.practice_id or request.status != PENDING:
        raise NotFound("join request not found")
    return request


async def _settle_notices(db: AsyncSession, actor: Actor, request_id: str) -> None:
    await db.execute(
        update(InboxItem)
        .where(
            InboxItem.practice_id == actor.practice_id,
            InboxItem.kind == JOIN_REQUESTED_KIND,
            InboxItem.payload["request_id"].astext == request_id,
            InboxItem.read_at.is_(None),
        )
        .values(read_at=utcnow())
    )
