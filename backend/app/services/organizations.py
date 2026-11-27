from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFound
from app.models import (
    CLOSED_STATUSES,
    HQ_REALM,
    Organization,
    OrganizationMembership,
    Practice,
    PracticeMembership,
    Provider,
    User,
)
from app.services.memberships import ACTIVE_MEMBER, SEAT_HOLDING

__all__ = [
    "ACTIVE_ORGANIZATION",
    "LIVE_ADMIN",
    "NOT_FOUND",
    "OrganizationChoice",
    "admin_ids",
    "organization_admin",
    "organization_admins",
    "organization_overview",
    "organization_practice",
    "organization_practices",
    "organizations_of",
    "practice_rows",
]

ACTIVE_ORGANIZATION = "active"
NOT_FOUND = "organization not found"
PRACTICE_NOT_FOUND = "practice not found in this organization"
LIVE_ADMIN = (OrganizationMembership.ended_at.is_(None), OrganizationMembership.role == "admin")


@dataclass(frozen=True)
class OrganizationChoice:
    id: str
    name: str
    role: str


async def organizations_of(db: AsyncSession, user: User) -> list[OrganizationChoice]:
    if user.realm == HQ_REALM:
        return []
    rows = await db.execute(
        select(Organization.id, Organization.name, OrganizationMembership.role)
        .join(OrganizationMembership, OrganizationMembership.organization_id == Organization.id)
        .where(
            OrganizationMembership.user_id == user.id,
            Organization.status == ACTIVE_ORGANIZATION,
            *LIVE_ADMIN,
        )
        .order_by(Organization.name, Organization.id)
    )
    return [OrganizationChoice(found, name, role) for found, name, role in rows.tuples()]


async def organization_admin(db: AsyncSession, user: User, organization_id: str) -> Organization:
    found = await db.scalar(
        select(Organization)
        .join(OrganizationMembership, OrganizationMembership.organization_id == Organization.id)
        .where(
            Organization.id == organization_id,
            Organization.status == ACTIVE_ORGANIZATION,
            OrganizationMembership.user_id == user.id,
            *LIVE_ADMIN,
        )
    )
    if found is None or user.realm == HQ_REALM:
        raise NotFound(NOT_FOUND)
    return found


async def organization_practices(db: AsyncSession, organization_id: str) -> list[Practice]:
    rows = await db.scalars(
        select(Practice).where(Practice.organization_id == organization_id).order_by(Practice.name, Practice.id)
    )
    return list(rows.all())


async def organization_practice(db: AsyncSession, organization: Organization, practice_id: str) -> Practice:
    practice = await db.get(Practice, practice_id, with_for_update=True)
    if practice is None or practice.organization_id != organization.id:
        raise NotFound(PRACTICE_NOT_FOUND)
    return practice


async def organization_admins(db: AsyncSession, organization_id: str) -> list[User]:
    rows = await db.scalars(
        select(User)
        .join(OrganizationMembership, OrganizationMembership.user_id == User.id)
        .where(OrganizationMembership.organization_id == organization_id, *LIVE_ADMIN)
        .order_by(User.name, User.id)
    )
    return list(rows.all())


async def admin_ids(db: AsyncSession, organization_id: str) -> set[str]:
    return {user.id for user in await organization_admins(db, organization_id)}


async def organization_overview(db: AsyncSession, organization: Organization, viewer: User) -> dict[str, Any]:
    return {
        "id": organization.id,
        "name": organization.name,
        "plan": organization.plan,
        "renews_on": organization.renews_on.isoformat() if organization.renews_on else None,
        "practices": await practice_rows(db, organization.id, viewer_id=viewer.id),
        "admins": [
            {"id": admin.id, "name": admin.name, "email": admin.email}
            for admin in await organization_admins(db, organization.id)
        ],
    }


async def practice_rows(
    db: AsyncSession, organization_id: str, *, viewer_id: str | None = None
) -> list[dict[str, Any]]:
    practices = await organization_practices(db, organization_id)
    ids = [practice.id for practice in practices]
    users = await _counts(db, PracticeMembership.practice_id, ids, *SEAT_HOLDING)
    providers = await _counts(db, Provider.practice_id, ids, Provider.active.is_(True))
    roles = await _roles_of(db, viewer_id, ids) if viewer_id is not None else None
    rows = []
    for practice in practices:
        row = {
            "id": practice.id,
            "name": practice.name,
            "status": practice.status,
            "plan": practice.plan,
            "renews_on": practice.renews_on.isoformat() if practice.renews_on else None,
            "combined_billing": practice.combined_billing,
            "users": users.get(practice.id, 0),
            "providers": providers.get(practice.id, 0),
            "open": practice.status not in CLOSED_STATUSES,
        }
        rows.append(row if roles is None else {**row, "my_role": roles.get(practice.id)})
    return rows


async def _roles_of(db: AsyncSession, user_id: str, practice_ids: list[str]) -> dict[str, str]:
    if not practice_ids:
        return {}
    rows = await db.execute(
        select(PracticeMembership.practice_id, PracticeMembership.role).where(
            PracticeMembership.user_id == user_id, PracticeMembership.practice_id.in_(practice_ids), *ACTIVE_MEMBER
        )
    )
    return dict(rows.tuples().all())


async def _counts(db: AsyncSession, column: Any, practice_ids: list[str], *conditions: Any) -> dict[str, int]:
    if not practice_ids:
        return {}
    rows = await db.execute(select(column, func.count()).where(column.in_(practice_ids), *conditions).group_by(column))
    return dict(rows.tuples().all())
