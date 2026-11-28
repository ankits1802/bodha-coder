from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from sqlalchemy import Select, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.calendar import today_in
from app.core.config import get_settings
from app.core.deps import Actor
from app.core.errors import Conflict, Invalid, NotFound
from app.models import (
    CLOSED_STATUSES,
    ORGANIZATION_CLOSED_STATUSES,
    DomainClaim,
    Organization,
    OrganizationMembership,
    Practice,
    Subscription,
    utcnow,
)
from app.services.audit_log import record_activity
from app.services.organization_billing import (
    ORGANIZATION_ZONE,
    follow_all,
    refuse_organization_change,
    set_combined,
)
from app.services.organization_plan import organization_plan
from app.services.organizations import LIVE_ADMIN, organization_admins, practice_rows
from app.services.plan_limits import combined_provider_count, organization_subscription
from app.services.plans import PLAN_KEYS, TRIAL
from app.services.retention import purge_after
from app.services.worklists import count_of

__all__ = [
    "CLOSED_ORGANIZATION",
    "attach_practice",
    "create_organization",
    "detach_practice",
    "hq_organization",
    "organization_count",
    "organization_page",
    "organization_rows",
    "release_organization_claims",
    "renew_organization",
    "set_practice_combined",
    "update_organization",
]

CLOSED_ORGANIZATION = "a closed organization cannot be changed"
ELSEWHERE = "this practice already belongs to another organization"
NOT_HERE = "this practice is not in the organization"
CLOSED_PRACTICE = "a closed practice cannot join an organization"
RENEWAL_IN_PAST = "choose a renewal date after today"


def _listed() -> Select[Any]:
    return select(Organization).order_by(Organization.name, Organization.id)


async def organization_count(db: AsyncSession) -> int:
    return await count_of(db, _listed())


async def organization_rows(db: AsyncSession, *, organization_id: str | None = None) -> list[dict[str, Any]]:
    query = _listed()
    found = await db.scalars(query if organization_id is None else query.where(Organization.id == organization_id))
    practices = await _counted(db, Practice.organization_id)
    combined = await _counted(db, Practice.organization_id, Practice.combined_billing.is_(True))
    admins = await _counted(db, OrganizationMembership.organization_id, *LIVE_ADMIN)
    billing = {row.organization_id: row for row in await db.scalars(select(Subscription).where(_organization_owned()))}
    return [
        await _row(db, organization, (practices, combined, admins), billing.get(organization.id))
        for organization in found
    ]


def _organization_owned() -> Any:
    return Subscription.organization_id.is_not(None)


async def _row(
    db: AsyncSession,
    organization: Organization,
    counts: tuple[dict[str, int], dict[str, int], dict[str, int]],
    subscription: Subscription | None,
) -> dict[str, Any]:
    practices, combined, admins = counts
    return {
        "id": organization.id,
        "name": organization.name,
        "status": organization.status,
        "plan": organization.plan,
        "renews_on": organization.renews_on.isoformat() if organization.renews_on else None,
        "practices": practices.get(organization.id, 0),
        "combined_practices": combined.get(organization.id, 0),
        "admins": admins.get(organization.id, 0),
        "providers": await combined_provider_count(db, organization.id),
        "created_on": organization.created_at.date().isoformat(),
        "closed_at": organization.closed_at.isoformat() if organization.closed_at else None,
        "purge_after": purge_after(organization.closed_at).isoformat() if organization.closed_at else None,
        "purged_at": organization.purged_at.isoformat() if organization.purged_at else None,
        "billing_provider": subscription.provider if subscription else None,
        "billing_status": subscription.status if subscription else None,
        "billing_interval": subscription.interval if subscription else None,
    }


async def _counted(db: AsyncSession, column: Any, *conditions: Any) -> dict[str, int]:
    rows = await db.execute(select(column, func.count()).where(column.is_not(None), *conditions).group_by(column))
    return dict(rows.tuples().all())


async def organization_page(db: AsyncSession, organization_id: str) -> dict[str, Any]:
    rows = await organization_rows(db, organization_id=organization_id)
    if not rows:
        raise NotFound("organization not found")
    organization = await db.get_one(Organization, organization_id)
    return {
        "organization": rows[0],
        "practices": await practice_rows(db, organization_id),
        "admins": [
            {
                "id": admin.id,
                "name": admin.name,
                "email": admin.email,
                "mfa_enabled": admin.mfa_enabled,
                "last_active_at": admin.last_active_at.isoformat() if admin.last_active_at else None,
            }
            for admin in await organization_admins(db, organization_id)
        ],
        "plan": await organization_plan(db, organization),
    }


async def hq_organization(db: AsyncSession, organization_id: str) -> Organization:
    organization = await db.get(Organization, organization_id, with_for_update=True, populate_existing=True)
    if organization is None:
        raise NotFound("organization not found")
    if organization.status in ORGANIZATION_CLOSED_STATUSES:
        raise Conflict(CLOSED_ORGANIZATION)
    return organization


async def create_organization(db: AsyncSession, actor: Actor, *, name: str, plan: str) -> Organization:
    if plan not in PLAN_KEYS:
        raise Invalid("choose a plan")
    renews_on = today_in(ORGANIZATION_ZONE) + timedelta(days=get_settings().trial_days) if plan == TRIAL else None
    organization = Organization(name=name.strip(), plan=plan, status="active", renews_on=renews_on)
    db.add(organization)
    await db.flush()
    record_activity(db, actor, "organization added", practice_id=None, detail=f"{organization.name}, {plan}")
    await db.commit()
    return organization


async def update_organization(
    db: AsyncSession, actor: Actor, organization_id: str, *, name: str | None, plan: str | None
) -> None:
    organization = await hq_organization(db, organization_id)
    if plan is not None and plan not in PLAN_KEYS:
        raise Invalid("choose a plan")
    changes = []
    if plan is not None and plan != organization.plan:
        refuse_organization_change(await organization_subscription(db, organization.id))
        changes.append({"field": "plan", "before": organization.plan, "after": plan})
        organization.plan = plan
    if name and name.strip() != organization.name:
        changes.append({"field": "name", "before": organization.name, "after": name.strip()})
        organization.name = name.strip()
    await follow_all(db, organization)
    detail = f"{organization.name}, {organization.plan}"
    record_activity(db, actor, "organization updated", practice_id=None, detail=detail, changes=changes)
    await db.commit()


async def renew_organization(
    db: AsyncSession, actor: Actor, organization_id: str, until: date | None, *, plan: str | None = None
) -> Organization:
    organization = await hq_organization(db, organization_id)
    refuse_organization_change(await organization_subscription(db, organization.id))
    if until is not None and until <= today_in(ORGANIZATION_ZONE):
        raise Invalid(RENEWAL_IN_PAST)
    if plan is not None and plan not in PLAN_KEYS:
        raise Invalid("choose a plan")
    previous, previous_plan = organization.renews_on, organization.plan
    organization.renews_on, organization.plan = until, plan or organization.plan
    await follow_all(db, organization)
    changed = [{"field": "renews_on", "before": _day(previous), "after": _day(until)}]
    if organization.plan != previous_plan:
        changed.append({"field": "plan", "before": previous_plan, "after": organization.plan})
    ends = f"renews {until.isoformat()}" if until else "no end date"
    detail = f"{organization.name}: {organization.plan}, {ends}"
    record_activity(db, actor, "organization renewed", practice_id=None, detail=detail, changes=changed)
    await db.commit()
    return organization


def _day(value: date | None) -> str | None:
    return value.isoformat() if value else None


async def attach_practice(db: AsyncSession, actor: Actor, organization_id: str, practice_id: str) -> None:
    organization = await hq_organization(db, organization_id)
    practice = await db.get(Practice, practice_id, with_for_update=True)
    if practice is None:
        raise NotFound("practice not found")
    if practice.status in CLOSED_STATUSES:
        raise Conflict(CLOSED_PRACTICE)
    if practice.organization_id == organization.id:
        return
    if practice.organization_id is not None:
        raise Conflict(ELSEWHERE)
    practice.organization_id = organization.id
    detail = f"{practice.name} into {organization.name}"
    record_activity(db, actor, "practice joined organization", practice_id=practice.id, detail=detail)
    await db.commit()


async def detach_practice(db: AsyncSession, actor: Actor, organization_id: str, practice_id: str) -> None:
    organization = await hq_organization(db, organization_id)
    practice = await _member_practice(db, organization, practice_id)
    await set_combined(db, actor, organization, practice, combined=False)
    practice.organization_id = None
    await release_organization_claims(db, actor, organization.id, practice_id=practice.id)
    detail = f"{practice.name} out of {organization.name}"
    record_activity(db, actor, "practice left organization", practice_id=practice.id, detail=detail)
    await db.commit()


async def set_practice_combined(
    db: AsyncSession, actor: Actor, organization_id: str, practice_id: str, *, combined: bool
) -> bool:
    organization = await hq_organization(db, organization_id)
    practice = await _member_practice(db, organization, practice_id)
    changed = await set_combined(db, actor, organization, practice, combined=combined)
    await db.commit()
    return changed


async def release_organization_claims(
    db: AsyncSession, actor: Actor, organization_id: str, *, practice_id: str | None = None
) -> None:
    statement = update(DomainClaim).where(
        DomainClaim.organization_id == organization_id, DomainClaim.released_at.is_(None)
    )
    if practice_id is not None:
        statement = statement.where(DomainClaim.practice_id == practice_id)
    await db.execute(statement.values(released_at=utcnow(), released_by=actor.user.id))


async def _member_practice(db: AsyncSession, organization: Organization, practice_id: str) -> Practice:
    practice = await db.get(Practice, practice_id, with_for_update=True)
    if practice is None or practice.organization_id != organization.id:
        raise NotFound(NOT_HERE)
    return practice
