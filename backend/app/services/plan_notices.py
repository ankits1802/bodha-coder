from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.calendar import zone_named
from app.core.deps import ACTIVE_PRACTICE_STATUSES
from app.models import InboxItem, Practice, Subscription
from app.services.inbox import Notice, notify_admins
from app.services.plan_limits import LIVE_STATUSES

__all__ = ["PAYMENT_FAILED_KIND", "PLAN_ENDING_DAYS", "PLAN_ENDING_KIND", "notify_plans_ending", "plan_ending_soon"]

PLAN_ENDING_DAYS = 3
PLAN_ENDING_KIND = "plan_ending"
PAYMENT_FAILED_KIND = "payment_failed"


def plan_ending_soon(renews_on: date | None, today: date) -> bool:
    return renews_on is not None and 0 <= (renews_on - today).days <= PLAN_ENDING_DAYS


async def notify_plans_ending(db: AsyncSession, now: datetime) -> int:
    live = select(Subscription.practice_id).where(
        Subscription.status.in_(LIVE_STATUSES), Subscription.practice_id.is_not(None)
    )
    paying = select(Subscription.organization_id).where(
        Subscription.status.in_(LIVE_STATUSES), Subscription.organization_id.is_not(None)
    )
    paid_together = Practice.combined_billing.is_(True) & Practice.organization_id.in_(paying)
    practices = await db.scalars(
        select(Practice).where(
            Practice.status.in_(ACTIVE_PRACTICE_STATUSES),
            Practice.renews_on.is_not(None),
            Practice.id.not_in(live),
            ~paid_together,
        )
    )
    told = 0
    for practice in practices.all():
        if plan_ending_soon(practice.renews_on, now.astimezone(zone_named(practice.time_zone)).date()):
            told += await _tell_admins(db, practice)
    await db.commit()
    return told


async def _tell_admins(db: AsyncSession, practice: Practice) -> int:
    ends_on = practice.renews_on.isoformat() if practice.renews_on else ""
    already = await db.scalars(
        select(InboxItem.user_id).where(
            InboxItem.practice_id == practice.id,
            InboxItem.kind == PLAN_ENDING_KIND,
            InboxItem.payload["ends_on"].astext == ends_on,
        )
    )
    notice = Notice(PLAN_ENDING_KIND, payload={"ends_on": ends_on})
    return len(await notify_admins(db, practice.id, notice, skip=already.all()))
