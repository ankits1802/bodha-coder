from __future__ import annotations

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.billing_contract import ProcessorSubscription
from app.core.config import get_settings
from app.core.deps import Actor
from app.core.errors import Conflict
from app.models import CLOSED_STATUSES, Organization, Practice, Subscription
from app.services.audit_log import record_activity
from app.services.inbox import Notice, notify_admins
from app.services.plan_limits import (
    active_provider_count,
    is_live,
    organization_subscription,
    subscription_for,
    user_count,
)
from app.services.plan_notices import PAYMENT_FAILED_KIND
from app.services.plans import TRIAL, plan_terms
from app.services.subscription_state import (
    ACTIVE,
    ENDED_STATUSES,
    HQ_DECIDED_STATUSES,
    PAST_DUE,
    SUBSCRIPTION_CHANGED,
    access_until,
    change_detail,
    grant_access,
    replaces,
    snapshot,
    write_state,
)

__all__ = [
    "COMBINED_JOINED",
    "COMBINED_LEFT",
    "ORGANIZATION_ZONE",
    "apply_organization_subscription",
    "combined_practices",
    "follow_all",
    "follow_organization",
    "refuse_organization_change",
    "set_combined",
]

logger = logging.getLogger("bodha.billing")
COMBINED_JOINED = "combined billing joined"
COMBINED_LEFT = "combined billing left"
CLOSED_PRACTICE = "a closed practice cannot change how it is billed"
ORGANIZATION_ZONE = ZoneInfo("UTC")
OWN_SUBSCRIPTION = "cancel this practice's own subscription before it joins combined billing"


async def combined_practices(db: AsyncSession, organization_id: str, *, lock: bool = False) -> list[Practice]:
    query = (
        select(Practice)
        .where(Practice.organization_id == organization_id, Practice.combined_billing.is_(True))
        .order_by(Practice.name, Practice.id)
    )
    return list((await db.scalars(query.with_for_update() if lock else query)).all())


def follow_organization(practice: Practice, organization: Organization, subscription: Subscription | None) -> None:
    if practice.status in HQ_DECIDED_STATUSES:
        return
    if subscription is not None and is_live(subscription):
        grant_access(practice, subscription, was_live=True, grace_days=get_settings().billing_grace_days)
        return
    practice.plan, practice.renews_on = organization.plan, organization.renews_on
    practice.status = TRIAL if organization.plan == TRIAL else ACTIVE


async def follow_all(db: AsyncSession, organization: Organization) -> None:
    subscription = await organization_subscription(db, organization.id)
    for practice in await combined_practices(db, organization.id, lock=True):
        follow_organization(practice, organization, subscription)


def refuse_organization_change(subscription: Subscription | None) -> None:
    if is_live(subscription):
        raise Conflict("this organization pays through a subscription; its plan and renewal follow the subscription")


async def set_combined(
    db: AsyncSession, actor: Actor, organization: Organization, practice: Practice, *, combined: bool
) -> bool:
    if practice.combined_billing == combined:
        return False
    if practice.status in CLOSED_STATUSES:
        raise Conflict(CLOSED_PRACTICE)
    if combined:
        await _ensure_can_join(db, organization, practice)
        practice.combined_billing = True
        follow_organization(practice, organization, await organization_subscription(db, organization.id))
    else:
        practice.combined_billing = False
    action = COMBINED_JOINED if combined else COMBINED_LEFT
    record_activity(db, actor, action, practice_id=practice.id, detail=f"{practice.name}, {organization.name}")
    return True


async def _ensure_can_join(db: AsyncSession, organization: Organization, practice: Practice) -> None:
    if is_live(await subscription_for(db, practice.id)):
        raise Conflict(OWN_SUBSCRIPTION)
    terms = plan_terms(organization.plan)
    providers = await active_provider_count(db, practice.id)
    if terms.max_providers is not None and providers > terms.max_providers:
        raise Conflict(f"the {terms.name} plan allows up to {terms.max_providers} active providers in each practice")
    users = await user_count(db, practice.id)
    if terms.max_users is not None and users > terms.max_users:
        raise Conflict(f"the {terms.name} plan allows up to {terms.max_users} users in each practice")


async def apply_organization_subscription(
    db: AsyncSession,
    organization_id: str,
    provider_name: str,
    state: ProcessorSubscription,
    chosen: tuple[str, str],
    *,
    payment: str | None,
    now: datetime,
) -> None:
    organization = await db.get(Organization, organization_id, with_for_update=True)
    if organization is None:
        logger.warning("%s subscription %s names no known organization", provider_name, state.subscription_id)
        return
    stored = await organization_subscription(db, organization.id, lock=True)
    if not replaces(stored, state):
        return
    same = stored is not None and stored.subscription_id == state.subscription_id
    was_live = same and is_live(stored)
    was_past_due = same and stored is not None and stored.status == PAST_DUE
    previous = snapshot(stored) if same else None
    row = stored or Subscription(organization_id=organization.id)
    if stored is None:
        db.add(row)
    write_state(row, provider_name, state, chosen, payment=payment, now=now, same=same)
    practices = await combined_practices(db, organization.id, lock=True)
    if organization.status == ACTIVE:
        _grant_organization(organization, row, was_live=was_live)
        for practice in practices:
            grant_access(practice, row, was_live=was_live, grace_days=get_settings().billing_grace_days)
    if snapshot(row) != previous:
        detail = f"{organization.name}: {change_detail(row)}"
        record_activity(db, None, SUBSCRIPTION_CHANGED, practice_id=None, detail=detail)
    if row.status == PAST_DUE and not was_past_due:
        await _tell_practices_payment_failed(db, practices)


def _grant_organization(organization: Organization, row: Subscription, *, was_live: bool) -> None:
    grace_days = get_settings().billing_grace_days
    if is_live(row):
        organization.plan = row.plan
        organization.renews_on = access_until(row, ORGANIZATION_ZONE, grace_days)
    elif row.status in ENDED_STATUSES and was_live:
        organization.renews_on = access_until(row, ORGANIZATION_ZONE, grace_days)


async def _tell_practices_payment_failed(db: AsyncSession, practices: list[Practice]) -> None:
    for practice in practices:
        until = practice.renews_on.isoformat() if practice.renews_on else ""
        await notify_admins(db, practice.id, Notice(PAYMENT_FAILED_KIND, payload={"access_until": until}))
