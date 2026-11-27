from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.adapters.billing_contract import PAYMENT_FAILED, ProcessorSubscription
from app.core.calendar import today_in, zone_named
from app.models import CLOSED_STATUSES, Practice, Subscription
from app.services.plan_limits import LIVE_STATUSES

__all__ = [
    "ACTIVE",
    "ENDED_STATUSES",
    "HQ_DECIDED_STATUSES",
    "PAST_DUE",
    "SUBSCRIPTION_CHANGED",
    "StateSnapshot",
    "access_until",
    "change_detail",
    "grant_access",
    "replaces",
    "snapshot",
    "write_state",
]

SUBSCRIPTION_CHANGED = "subscription changed"
ACTIVE, PAST_DUE = "active", "past_due"
ENDED_STATUSES = ("canceled", "expired")
HQ_DECIDED_STATUSES = ("ended", "blocked", *CLOSED_STATUSES)
StateSnapshot = tuple[object, ...]


def access_until(row: Subscription, zone: ZoneInfo, grace_days: int) -> date:
    if row.past_due_since is not None:
        return (row.past_due_since + timedelta(days=grace_days)).astimezone(zone).date()
    if row.current_period_end is not None:
        return row.current_period_end.astimezone(zone).date()
    return today_in(zone)


def grant_access(practice: Practice, row: Subscription, *, was_live: bool, grace_days: int) -> None:
    zone = zone_named(practice.time_zone)
    if row.status in LIVE_STATUSES:
        practice.status, practice.plan = ACTIVE, row.plan
        practice.renews_on = access_until(row, zone, grace_days)
    elif row.status in ENDED_STATUSES and was_live:
        practice.renews_on = access_until(row, zone, grace_days)


def replaces(stored: Subscription | None, state: ProcessorSubscription) -> bool:
    if stored is None or stored.subscription_id == state.subscription_id:
        return True
    return state.status in LIVE_STATUSES or stored.status not in LIVE_STATUSES


def write_state(
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


def snapshot(row: Subscription | None) -> StateSnapshot | None:
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


def change_detail(row: Subscription) -> str:
    ending = ", ends at period end" if row.cancel_at_period_end else ""
    return f"{row.provider} {row.plan} {row.interval}: {row.status}{ending}, {row.quantity} providers"
