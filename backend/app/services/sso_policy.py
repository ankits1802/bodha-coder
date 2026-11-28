from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.saml_metadata import ServiceProvider
from app.core.config import get_settings
from app.core.deps import ACTIVE_PRACTICE_STATUSES
from app.core.errors import Forbidden
from app.models import (
    CLOSED_STATUSES,
    PRACTICE_REALM,
    DomainClaim,
    Organization,
    Practice,
    SsoConnection,
    SsoVersion,
    User,
)
from app.services.email_domains import domain_of, is_public_domain

__all__ = [
    "SSO_REQUIRED",
    "SsoRequired",
    "SsoRoute",
    "connection_for_claim",
    "current_version",
    "ensure_password_allowed",
    "ensure_service_allowed",
    "owner_practice_ids",
    "requires_sso",
    "route_for_email",
    "service_provider",
    "signs_in_with_sso",
]

SSO_REQUIRED = "your organization signs in with single sign-on"
ACTIVE_ORGANIZATION = "active"
SAML_PATH = "/api/auth/saml/{connection_id}"


class SsoRequired(Forbidden):
    code = "sso_required"

    def __init__(self) -> None:
        super().__init__(SSO_REQUIRED)


@dataclass(frozen=True)
class SsoRoute:
    connection: SsoConnection
    version: SsoVersion
    claim: DomainClaim

    @property
    def required(self) -> bool:
        return self.version.required

    def keeps_password(self, user: User | None) -> bool:
        return user is not None and user.id in self.version.break_glass


def service_provider(connection_id: str) -> ServiceProvider:
    base = get_settings().app_url.rstrip("/") + SAML_PATH.format(connection_id=connection_id)
    return ServiceProvider(entity_id=f"{base}/metadata", acs_url=f"{base}/acs")


async def current_version(db: AsyncSession, connection_id: str) -> SsoVersion | None:
    return await db.scalar(
        select(SsoVersion).where(SsoVersion.connection_id == connection_id).order_by(SsoVersion.version.desc()).limit(1)
    )


async def connection_for_claim(db: AsyncSession, claim: DomainClaim) -> SsoConnection | None:
    owner = (
        SsoConnection.organization_id == claim.organization_id
        if claim.organization_id is not None
        else SsoConnection.practice_id == claim.practice_id
    )
    return await db.scalar(select(SsoConnection).where(owner, SsoConnection.removed_at.is_(None)))


async def owner_practice_ids(db: AsyncSession, *, practice_id: str | None, organization_id: str | None) -> list[str]:
    if organization_id is None:
        return [practice_id] if practice_id else []
    rows = await db.scalars(
        select(Practice.id)
        .where(Practice.organization_id == organization_id, Practice.status.not_in(CLOSED_STATUSES))
        .order_by(Practice.name, Practice.id)
    )
    return list(rows.all())


async def route_for_email(db: AsyncSession, email: str) -> SsoRoute | None:
    domain = domain_of(email)
    if domain is None or is_public_domain(domain):
        return None
    claim = await db.scalar(
        select(DomainClaim).where(
            DomainClaim.domain == domain, DomainClaim.verified_at.is_not(None), DomainClaim.released_at.is_(None)
        )
    )
    if claim is None or not await _owner_open(db, claim):
        return None
    connection = await connection_for_claim(db, claim)
    version = await current_version(db, connection.id) if connection is not None else None
    if connection is None or version is None or claim.id not in version.claim_ids:
        return None
    return SsoRoute(connection, version, claim)


async def signs_in_with_sso(db: AsyncSession, user: User) -> bool:
    if user.realm != PRACTICE_REALM:
        return False
    route = await route_for_email(db, user.email)
    return route is not None and route.required and not route.keeps_password(user)


async def ensure_password_allowed(db: AsyncSession, email: str, user: User | None) -> SsoRoute | None:
    if user is not None and user.realm != PRACTICE_REALM:
        return None
    route = await route_for_email(db, email)
    if route is not None and route.required and not route.keeps_password(user):
        raise SsoRequired()
    return route


async def requires_sso(db: AsyncSession, email: str) -> bool:
    route = await route_for_email(db, email)
    return route is not None and route.required


async def ensure_service_allowed(db: AsyncSession, email: str) -> None:
    if await requires_sso(db, email):
        raise SsoRequired()


async def _owner_open(db: AsyncSession, claim: DomainClaim) -> bool:
    if claim.organization_id is not None:
        organization = await db.get(Organization, claim.organization_id)
        return organization is not None and organization.status == ACTIVE_ORGANIZATION
    practice = await db.get(Practice, claim.practice_id)
    return practice is not None and practice.status in ACTIVE_PRACTICE_STATUSES
