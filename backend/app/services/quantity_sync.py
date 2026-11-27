from __future__ import annotations

import logging
from collections.abc import Mapping

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.billing_contract import BillingProvider, BillingUnavailable
from app.models import Practice, Subscription
from app.services.audit_log import record_activity
from app.services.plan_limits import LIVE_STATUSES, active_provider_count, combined_provider_count
from app.services.subscriptions import subscription_ref

__all__ = ["QUANTITY_CHANGED", "billed_providers", "sync_quantities"]

logger = logging.getLogger("bodha.billing")
QUANTITY_CHANGED = "subscription quantity changed"


async def sync_quantities(
    db: AsyncSession,
    providers: Mapping[str, BillingProvider],
    *,
    practice_id: str | None = None,
    organization_id: str | None = None,
) -> int:
    query = select(Subscription.id).where(Subscription.status.in_(LIVE_STATUSES))
    if practice_id is not None:
        paying = select(Practice.organization_id).where(Practice.id == practice_id, Practice.combined_billing)
        query = query.where(
            or_(Subscription.practice_id == practice_id, Subscription.organization_id.in_(paying.scalar_subquery()))
        )
    if organization_id is not None:
        query = query.where(Subscription.organization_id == organization_id)
    changed = 0
    for row_id in (await db.scalars(query)).all():
        if await _sync_one(db, providers, row_id):
            changed += 1
    return changed


async def billed_providers(db: AsyncSession, row: Subscription) -> int:
    if row.organization_id is not None:
        return max(1, await combined_provider_count(db, row.organization_id))
    return max(1, await active_provider_count(db, row.practice_id or ""))


async def _sync_one(db: AsyncSession, providers: Mapping[str, BillingProvider], row_id: str) -> bool:
    row = await db.get(Subscription, row_id, with_for_update=True)
    provider = providers.get(row.provider) if row is not None else None
    if row is None or provider is None or row.status not in LIVE_STATUSES:
        await db.rollback()
        return False
    wanted = await billed_providers(db, row)
    if wanted == row.quantity:
        await db.rollback()
        return False
    try:
        await provider.set_quantity(subscription_ref(row), wanted)
    except BillingUnavailable:
        logger.warning("a subscription quantity was not changed yet; retrying later")
        await db.rollback()
        return False
    row.quantity = wanted
    record_activity(
        db, None, QUANTITY_CHANGED, practice_id=row.practice_id, detail=f"{row.provider}: {wanted} providers"
    )
    await db.commit()
    return True
