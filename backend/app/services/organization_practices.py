from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.calendar import zone_named
from app.core.config import get_settings
from app.core.deps import Actor, Client
from app.core.errors import Invalid
from app.models import Organization, Practice, utcnow
from app.services.audit_log import record_activity, record_practice_access
from app.services.organization_billing import follow_organization, set_combined
from app.services.organizations import organization_practice
from app.services.plan_limits import organization_subscription
from app.services.plans import TRIAL, plan_terms
from app.services.practice_accounts import PracticeDraft, add_practice_for_person

__all__ = ["LOCATION_ADDED", "ORGANIZATION_SOURCE", "Location", "add_location", "set_practice_billing"]

LOCATION_ADDED = "practice added by organization"
ORGANIZATION_SOURCE = "organization"
DEFAULT_SEATS = 10
ACTIVE = "active"


@dataclass(frozen=True)
class Location:
    name: str
    time_zone: str
    agreed: bool


async def add_location(db: AsyncSession, actor: Actor, organization: Organization, location: Location) -> Practice:
    if location.agreed is not True:
        raise Invalid("agree to the terms to add a practice")
    zone = zone_named(location.time_zone)
    terms = plan_terms(organization.plan)
    status = TRIAL if organization.plan == TRIAL else ACTIVE
    signup = _signup_record(actor.user.id, actor.client)
    draft = PracticeDraft(
        location.name,
        organization.plan,
        status,
        terms.max_users or DEFAULT_SEATS,
        zone.key,
        renews_on=organization.renews_on,
        signup=signup,
    )
    created = await add_practice_for_person(db, draft, actor.user)
    practice = created.practice
    practice.organization_id, practice.combined_billing = organization.id, True
    follow_organization(practice, organization, await organization_subscription(db, organization.id))
    detail = f"{practice.name} in {organization.name}"
    record_activity(db, actor, LOCATION_ADDED, practice_id=practice.id, detail=detail)
    record_practice_access(db, practice.id, actor.user, LOCATION_ADDED, detail=detail, client=actor.client)
    await db.commit()
    return practice


def _signup_record(user_id: str, client: Client) -> dict[str, Any]:
    return {
        "source": ORGANIZATION_SOURCE,
        "agreement_version": get_settings().agreement_version,
        "accepted_at": utcnow().isoformat(),
        "accepted_by": user_id,
        "method": ORGANIZATION_SOURCE,
        "ip": client.ip,
    }


async def set_practice_billing(
    db: AsyncSession, actor: Actor, organization: Organization, practice_id: str, *, combined: bool
) -> bool:
    practice = await organization_practice(db, organization, practice_id)
    changed = await set_combined(db, actor, organization, practice, combined=combined)
    await db.commit()
    return changed
