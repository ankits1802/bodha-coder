from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.messenger import Messenger
from app.core.config import get_settings
from app.core.deps import Actor
from app.core.errors import Conflict, NotFound
from app.models import PRACTICE_REALM, OrganizationMembership, User, utcnow
from app.services.account_lookup import account_by_email
from app.services.audit_log import record_activity
from app.services.hq_organizations import hq_organization

__all__ = [
    "ORGANIZATION_ADMIN_ADDED",
    "ORGANIZATION_ADMIN_REMOVED",
    "add_organization_admin",
    "remove_organization_admin",
]

ORGANIZATION_ADMIN_ADDED = "organization admin added"
ORGANIZATION_ADMIN_REMOVED = "organization admin removed"
ADMIN_ROLE = "admin"
NO_ACCOUNT = "this email has no practice account; add the person to a practice first"
ALREADY_ADMIN = "this person is already an admin of the organization"


async def add_organization_admin(
    db: AsyncSession, messenger: Messenger, actor: Actor, organization_id: str, *, email: str, reason: str
) -> User:
    organization = await hq_organization(db, organization_id)
    person = await account_by_email(db, email, (PRACTICE_REALM,))
    if person is None:
        raise NotFound(NO_ACCOUNT)
    membership = await _membership(db, person.id, organization.id)
    if membership is not None and membership.ended_at is None:
        raise Conflict(ALREADY_ADMIN)
    if membership is None:
        membership = OrganizationMembership(user_id=person.id, organization_id=organization.id, role=ADMIN_ROLE)
        db.add(membership)
    membership.ended_at, membership.added_by, membership.role = None, actor.user.id, ADMIN_ROLE
    detail = f"{person.name} in {organization.name}: {reason}"
    record_activity(db, actor, ORGANIZATION_ADMIN_ADDED, practice_id=None, detail=detail)
    await db.commit()
    await messenger.email(
        person.email,
        subject=f"You're an admin of {organization.name}",
        body=(
            f"{person.name}, Bodha HQ made you an admin of {organization.name} on Bodha Assure. "
            f"Sign in: {get_settings().app_url}/sign-in"
        ),
    )
    return person


async def remove_organization_admin(db: AsyncSession, actor: Actor, organization_id: str, user_id: str) -> None:
    organization = await hq_organization(db, organization_id)
    membership = await _membership(db, user_id, organization.id)
    person = await db.get(User, user_id)
    if membership is None or membership.ended_at is not None or person is None:
        raise NotFound("organization admin not found")
    membership.ended_at = utcnow()
    record_activity(
        db, actor, ORGANIZATION_ADMIN_REMOVED, practice_id=None, detail=f"{person.name} from {organization.name}"
    )
    await db.commit()


async def _membership(db: AsyncSession, user_id: str, organization_id: str) -> OrganizationMembership | None:
    return await db.scalar(
        select(OrganizationMembership)
        .where(OrganizationMembership.user_id == user_id, OrganizationMembership.organization_id == organization_id)
        .with_for_update()
    )
