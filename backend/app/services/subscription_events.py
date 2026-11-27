from __future__ import annotations

import logging
from collections.abc import Mapping
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.billing_contract import PAYMENT_FAILED, BillingProvider, ProcessorEvent, ProcessorSubscription
from app.core.calendar import today_in, zone_named
from app.core.config import get_settings
from app.models import BillingEvent, Practice, Subscription, utcnow
from app.services.audit_log import record_activity
from app.services.plan_limits import LIVE_STATUSES, is_live, subscription_for
from app.services.plans import plan_for_price

__all__ = ["SUBSCRIPTION_CHANGED", "access_until", "apply_subscription", "receive_webhook"]

logger = logging.getLogger("bodha.billing")
SUBSCRIPTION_CHANGED = "subscription changed"
ACTIVE, PAST_DUE = "active", "past_due"
ENDED_STATUSES = ("canceled", "expired")
HQ_DECIDED_STATUSES = ("ended", "blocked")
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
    practice = await _practice_for(db, provider_name, state)
    if practice is None:
        return
    chosen = plan_for_price(get_settings(), provider_name, state.price_id)
    if chosen is None:
        logger.error("%s subscription %s has a price no plan uses", provider_name, state.subscription_id)
        return
    stored = await subscription_for(db, practice.id, lock=True)
    if not _replaces(stored, state):
        return
    same = stored is not None and stored.subscription_id == state.subscription_id
    was_live = same and is_live(stored)
    previous = _snapshot(stored) if same else None
    row = stored or Subscription(practice_id=practice.id)
    if stored is None:
        db.add(row)
    _write_state(row, provider_name, state, chosen, payment=payment, now=now, same=same)
    if practice.status not in HQ_DECIDED_STATUSES:
        _grant_access(practice, row, was_live=was_live)
    if _snapshot(row) != previous:
        record_activity(db, None, SUBSCRIPTION_CHANGED, practice_id=practice.id, detail=_detail(row))


def access_until(row: Subscription, zone: ZoneInfo, grace_days: int) -> date:
    if row.past_due_since is not None:
        return (row.past_due_since + timedelta(days=grace_days)).astimezone(zone).date()
    if row.current_period_end is not None:
        return row.current_period_end.astimezone(zone).date()
    return today_in(zone)


async def _first_delivery(db: AsyncSession, provider_name: str, event: ProcessorEvent) -> bool:
    statement = (
        insert(BillingEvent)
        .values(
            provider=provider_name, event_id=event.event_id, kind=event.kind[:EVENT_KIND_LENGTH], received_at=utcnow()
        )
        .on_conflict_do_nothing()
        .returning(BillingEvent.event_id)
    )
    return await db.scalar(statement) is not None


async def _practice_for(db: AsyncSession, provider_name: str, state: ProcessorSubscription) -> Practice | None:
    practice_id = state.practice_id
    if practice_id is None:
        practice_id = await db.scalar(
            select(Subscription.practice_id).where(
                Subscription.provider == provider_name, Subscription.subscription_id == state.subscription_id
            )
        )
    practice = await db.get(Practice, practice_id, with_for_update=True) if practice_id else None
    if practice is None:
        logger.warning("%s subscription %s names no known practice", provider_name, state.subscription_id)
    return practice


def _replaces(stored: Subscription | None, state: ProcessorSubscription) -> bool:
    if stored is None or stored.subscription_id == state.subscription_id:
        return True
    return state.status in LIVE_STATUSES or stored.status not in LIVE_STATUSES


def _write_state(
    row: Subscription,
    provider_name: str,
    state: ProcessorSubscription,
    chosen: tuple[str, str],
    *,
    payment: str | None,
    now: datetime,
    same: bool,
) -> None:
    status = PAST_DUE if payment == PAYMENT_FAILED and state.status == ACTIVE else state.status
    if not same:
        row.current_period_end, row.past_due_since, row.customer_id = None, None, None
    row.provider, row.subscription_id = provider_name, state.subscription_id
    row.customer_id = state.customer_id or row.customer_id
    row.plan, row.interval = chosen
    row.status = status
    row.current_period_end = state.current_period_end or row.current_period_end
    row.cancel_at_period_end = state.cancel_at_period_end
    row.quantity = max(1, state.quantity)
    if status == ACTIVE:
        row.past_due_since = None
    elif status == PAST_DUE:
        row.past_due_since = row.past_due_since or now


def _grant_access(practice: Practice, row: Subscription, *, was_live: bool) -> None:
    grace_days = get_settings().billing_grace_days
    zone = zone_named(practice.time_zone)
    if row.status in LIVE_STATUSES:
        practice.status, practice.plan = ACTIVE, row.plan
        practice.renews_on = access_until(row, zone, grace_days)
    elif row.status in ENDED_STATUSES and was_live:
        practice.renews_on = access_until(row, zone, grace_days)


def _snapshot(row: Subscription | None) -> tuple[object, ...] | None:
    if row is None:
        return None
    return (
        row.provider,
        row.plan,
        row.interval,
        row.status,
        row.current_period_end,
        row.cancel_at_period_end,
        row.quantity,
    )


def _detail(row: Subscription) -> str:
    ending = ", ends at period end" if row.cancel_at_period_end else ""
    return f"{row.provider} {row.plan} {row.interval}: {row.status}{ending}, {row.quantity} providers"
