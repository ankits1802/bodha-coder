from __future__ import annotations

import logging
from datetime import timedelta

from sqlalchemy import Integer, String, bindparam, func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.object_store import ObjectStore, person_prefix
from app.core.config import get_settings
from app.core.deps import Actor
from app.core.errors import Conflict, Invalid, NotFound
from app.models import Organization, OrganizationMembership, Practice, User, utcnow
from app.services.audit_log import record_activity
from app.services.hq_organizations import release_organization_claims
from app.services.organization_billing import set_combined
from app.services.plan_limits import is_live, organization_subscription

__all__ = ["ORGANIZATION_CLOSED", "ORGANIZATION_PURGED", "close_organization", "purge_organization"]

logger = logging.getLogger("bodha.retention")
ORGANIZATION_CLOSED, ORGANIZATION_PURGED = "organization closed", "organization purged"
PURGE_ORGANIZATION = text("SELECT bodha_purge_organization(:organization, :days)").bindparams(
    bindparam("organization", type_=String), bindparam("days", type_=Integer)
)


async def close_organization(db: AsyncSession, actor: Actor, organization_id: str, *, confirm_name: str) -> None:
    organization = await _confirmed(db, organization_id, confirm_name, verb="close")
    if organization.status != "active":
        raise Conflict("this organization is already closed")
    if is_live(await organization_subscription(db, organization.id)):
        raise Conflict("cancel the organization's subscription before closing it")
    practices = await db.scalars(select(Practice).where(Practice.organization_id == organization.id).with_for_update())
    for practice in practices.all():
        await set_combined(db, actor, organization, practice, combined=False)
        practice.organization_id = None
        detail = f"{practice.name} out of {organization.name}"
        record_activity(db, actor, "practice left organization", practice_id=practice.id, detail=detail)
    await release_organization_claims(db, actor, organization.id)
    await db.execute(
        update(OrganizationMembership)
        .where(OrganizationMembership.organization_id == organization.id, OrganizationMembership.ended_at.is_(None))
        .values(ended_at=utcnow())
    )
    organization.status, organization.closed_at, organization.closed_by = "closed", utcnow(), actor.user.id
    record_activity(db, actor, ORGANIZATION_CLOSED, practice_id=None, detail=organization.name)
    await db.commit()


async def purge_organization(
    db: AsyncSession, store: ObjectStore, actor: Actor, organization_id: str, *, confirm_name: str
) -> int:
    organization = await _confirmed(db, organization_id, confirm_name, verb="purge")
    if organization.status != "closed" or organization.closed_at is None:
        raise Conflict("only a closed organization can be purged")
    days = get_settings().retention_days
    kept_until = organization.closed_at + timedelta(days=days)
    if await db.scalar(select(func.clock_timestamp())) < kept_until:
        raise Conflict(f"records are kept until {kept_until.date().isoformat()}; purge after that day")
    members = set(
        await db.scalars(
            select(OrganizationMembership.user_id).where(OrganizationMembership.organization_id == organization.id)
        )
    )
    removed = await db.scalar(PURGE_ORGANIZATION, {"organization": organization.id, "days": days}) or 0
    record_activity(db, actor, ORGANIZATION_PURGED, practice_id=None, detail=f"{organization.name}: {removed} rows")
    await db.commit()
    remaining = set(await db.scalars(select(User.id).where(User.id.in_(members))))
    for user_id in sorted(members - remaining):
        try:
            await store.delete_prefix(person_prefix(user_id))
        except Exception:
            logger.exception("stored signatures of a purged person were not removed")
    return removed


async def _confirmed(db: AsyncSession, organization_id: str, confirm_name: str, *, verb: str) -> Organization:
    organization = await db.get(Organization, organization_id, with_for_update=True, populate_existing=True)
    if organization is None:
        raise NotFound("organization not found")
    if confirm_name.strip() != organization.name:
        raise Invalid(f"type the organization name exactly as shown to {verb} it")
    return organization
