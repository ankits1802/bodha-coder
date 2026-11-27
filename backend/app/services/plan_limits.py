from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import Conflict
from app.models import Practice, Provider, Subscription, User
from app.services.plans import plan_terms

__all__ = [
    "LIVE_STATUSES",
    "active_provider_count",
    "ensure_provider_room",
    "ensure_user_room",
    "is_live",
    "provider_limit",
    "subscription_for",
    "user_count",
    "user_limit",
]

LIVE_STATUSES = ("active", "past_due")


def is_live(subscription: Subscription | None) -> bool:
    return subscription is not None and subscription.status in LIVE_STATUSES


async def subscription_for(db: AsyncSession, practice_id: str, *, lock: bool = False) -> Subscription | None:
    query = select(Subscription).where(Subscription.practice_id == practice_id)
    return await db.scalar(query.with_for_update() if lock else query)


async def active_provider_count(db: AsyncSession, practice_id: str) -> int:
    found = await db.scalar(
        select(func.count()).select_from(Provider).where(Provider.practice_id == practice_id, Provider.active.is_(True))
    )
    return found or 0


async def user_count(db: AsyncSession, practice_id: str) -> int:
    found = await db.scalar(
        select(func.count()).select_from(User).where(User.practice_id == practice_id, User.status != "blocked")
    )
    return found or 0


def user_limit(practice: Practice, subscription: Subscription | None) -> int | None:
    plan_users = plan_terms(practice.plan).max_users
    if is_live(subscription):
        return plan_users
    return practice.seats if plan_users is None else min(plan_users, practice.seats)


def provider_limit(practice: Practice) -> int | None:
    return plan_terms(practice.plan).max_providers


async def ensure_user_room(db: AsyncSession, practice: Practice) -> None:
    terms = plan_terms(practice.plan)
    used = await user_count(db, practice.id)
    if terms.max_users is not None and used >= terms.max_users:
        raise Conflict(f"the {terms.name} plan allows up to {terms.max_users} users")
    if not is_live(await subscription_for(db, practice.id)) and used >= practice.seats:
        raise Conflict("all seats are in use")


async def ensure_provider_room(db: AsyncSession, practice: Practice, adding: int) -> None:
    terms = plan_terms(practice.plan)
    if terms.max_providers is None or adding < 1:
        return
    if await active_provider_count(db, practice.id) + adding > terms.max_providers:
        raise Conflict(f"the {terms.name} plan allows up to {terms.max_providers} active providers")
