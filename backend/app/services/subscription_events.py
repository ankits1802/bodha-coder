from __future__ import annotations

import logging
from collections.abc import Mapping
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.billing_contract import BillingProvider, ProcessorEvent, ProcessorSubscription
from app.core.config import get_settings
from app.models import BillingEvent, Practice, Subscription, utcnow
from app.services.audit_log import record_activity
from app.services.inbox import Notice, notify_admins
from app.services.organization_billing import apply_organization_subscription
from app.services.plan_limits import is_live, subscription_for
from app.services.plan_notices import PAYMENT_FAILED_KIND
from app.services.plans import plan_for_price
from app.services.subscription_state import (
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

__all__ = ["SUBSCRIPTION_CHANGED", "access_until", "apply_subscription", "receive_webhook"]

logger = logging.getLogger("bodha.billing")
EVENT_KIND_LENGTH = 80


async def receive_webhook(db: AsyncSession, provider: BillingProvider, body: bytes, headers: Mapping[str, str]) -> None:
    event = await provider.read_event(body, headers)
    if not await _first_delivery(db, provider.name, event):
        return
    if event.subscription_id is not None:
        state = await provider.subscription(event.subscription_id)
        await apply_subscription(db, provider.name, state, payment=event.payment, now=utcnow())
    await db.commit()


async def apply_subscription(
    db: AsyncSession, provider_name: str, state: ProcessorSubscription, *, payment: str | None, now: datetime
) -> None:
    organization_id = await _organization_for(db, provider_name, state)
    practice = None if organization_id else await _practice_for(db, provider_name, state)
    if organization_id is None and practice is None:
        return
    chosen = plan_for_price(get_settings(), provider_name, state.price_id)
    if chosen is None:
        logger.error("%s subscription %s has a price no plan uses", provider_name, state.subscription_id)
        return
    if organization_id is not None:
        await apply_organization_subscription(
            db, organization_id, provider_name, state, chosen, payment=payment, now=now
        )
    elif practice is not None:
        await _apply_to_practice(db, practice, provider_name, state, chosen, payment=payment, now=now)


async def _apply_to_practice(
    db: AsyncSession,
    practice: Practice,
    provider_name: str,
    state: ProcessorSubscription,
    chosen: tuple[str, str],
    *,
    payment: str | None,
    now: datetime,
) -> None:
    stored = await subscription_for(db, practice.id, lock=True)
    if not replaces(stored, state):
        return
    same = stored is not None and stored.subscription_id == state.subscription_id
    was_live = same and is_live(stored)
    was_past_due = same and stored is not None and stored.status == PAST_DUE
    previous = snapshot(stored) if same else None
    row = stored or Subscription(practice_id=practice.id)
    if stored is None:
        db.add(row)
    write_state(row, provider_name, state, chosen, payment=payment, now=now, same=same)
    if practice.status not in HQ_DECIDED_STATUSES:
        grant_access(practice, row, was_live=was_live, grace_days=get_settings().billing_grace_days)
    if snapshot(row) != previous:
        record_activity(db, None, SUBSCRIPTION_CHANGED, practice_id=practice.id, detail=change_detail(row))
    if row.status == PAST_DUE and not was_past_due:
        await _tell_admins_payment_failed(db, practice)


async def _tell_admins_payment_failed(db: AsyncSession, practice: Practice) -> None:
    until = practice.renews_on.isoformat() if practice.renews_on else ""
    await notify_admins(db, practice.id, Notice(PAYMENT_FAILED_KIND, payload={"access_until": until}))


async def _first_delivery(db: AsyncSession, provider_name: str, event: ProcessorEvent) -> bool:
    statement = (
        insert(BillingEvent)
        .values(provider=provider_name, event_id=event.event_id, kind=event.kind[:EVENT_KIND_LENGTH])
        .on_conflict_do_nothing()
        .returning(BillingEvent.event_id)
    )
    return await db.scalar(statement) is not None


async def _stored_owner(db: AsyncSession, provider_name: str, subscription_id: str) -> Subscription | None:
    return await db.scalar(
        select(Subscription).where(
            Subscription.provider == provider_name, Subscription.subscription_id == subscription_id
        )
    )


async def _organization_for(db: AsyncSession, provider_name: str, state: ProcessorSubscription) -> str | None:
    if state.organization_id is not None:
        return state.organization_id
    if state.practice_id is not None:
        return None
    stored = await _stored_owner(db, provider_name, state.subscription_id)
    return stored.organization_id if stored is not None else None


async def _practice_for(db: AsyncSession, provider_name: str, state: ProcessorSubscription) -> Practice | None:
    practice_id = state.practice_id
    if practice_id is None:
        stored = await _stored_owner(db, provider_name, state.subscription_id)
        practice_id = stored.practice_id if stored is not None else None
    practice = await db.get(Practice, practice_id, with_for_update=True) if practice_id else None
    if practice is None:
        logger.warning("%s subscription %s names no known practice", provider_name, state.subscription_id)
    return practice
