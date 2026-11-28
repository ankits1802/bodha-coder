from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import RateLimited
from app.core.security import digest
from app.models import RateEvent, utcnow

UNKNOWN_KEY = "unknown"
PURGE_BATCH = 200


@dataclass(frozen=True)
class RateRule:
    bucket: str
    limit: int
    window: timedelta


LOGIN_PER_EMAIL = RateRule("login_email", 10, timedelta(minutes=15))
LOGIN_PER_IP = RateRule("login_ip", 30, timedelta(minutes=15))
FORGOT_PER_EMAIL = RateRule("forgot_email", 3, timedelta(hours=1))
FORGOT_PER_IP = RateRule("forgot_ip", 10, timedelta(hours=1))
MFA_PER_USER = RateRule("mfa_user", 10, timedelta(minutes=15))
IDENTITY_PER_IP = RateRule("identity_ip", 30, timedelta(minutes=15))
PROVIDER_CODE_PER_REQUEST = RateRule("provider_code", 5, timedelta(hours=1))
DEMO_PER_IP = RateRule("demo_ip", 5, timedelta(hours=1))
SIGNUP_PER_IP = RateRule("signup_ip", 5, timedelta(hours=1))
SIGNUP_PER_EMAIL = RateRule("signup_email", 3, timedelta(hours=1))
SIGNATURE_DRAFTS_PER_OWNER = RateRule("signature_drafts", 20, timedelta(hours=1))
VERIFY_PER_IP = RateRule("verify_ip", 30, timedelta(minutes=15))
DOMAIN_CHECKS_PER_CLAIM = RateRule("domain_check", 10, timedelta(hours=1))
DOMAIN_EMAILS_PER_CLAIM = RateRule("domain_email", 3, timedelta(hours=1))
DOMAIN_LINKS_PER_IP = RateRule("domain_link_ip", 30, timedelta(minutes=15))
INTAKE_TESTS_PER_PRACTICE = RateRule("intake_test", 5, timedelta(hours=1))
EHR_TESTS_PER_PRACTICE = RateRule("ehr_test", 10, timedelta(hours=1))
RULES = (
    LOGIN_PER_EMAIL,
    LOGIN_PER_IP,
    FORGOT_PER_EMAIL,
    FORGOT_PER_IP,
    MFA_PER_USER,
    IDENTITY_PER_IP,
    PROVIDER_CODE_PER_REQUEST,
    DEMO_PER_IP,
    SIGNUP_PER_IP,
    SIGNUP_PER_EMAIL,
    SIGNATURE_DRAFTS_PER_OWNER,
    VERIFY_PER_IP,
    DOMAIN_CHECKS_PER_CLAIM,
    DOMAIN_EMAILS_PER_CLAIM,
    DOMAIN_LINKS_PER_IP,
    INTAKE_TESTS_PER_PRACTICE,
    EHR_TESTS_PER_PRACTICE,
)
LONGEST_WINDOW = max(rule.window for rule in RULES)


async def hit(db: AsyncSession, rule: RateRule, key: str | None) -> None:
    now = utcnow()
    key_hash = digest(key or UNKNOWN_KEY)
    same_key = (RateEvent.bucket == rule.bucket, RateEvent.key_hash == key_hash)
    await db.execute(select(func.pg_advisory_xact_lock(func.hashtextextended(f"{rule.bucket}:{key_hash}", 0))))
    await db.execute(delete(RateEvent).where(*same_key, RateEvent.created_at <= now - rule.window))
    await _purge_stale(db, now)
    count, oldest = (await db.execute(select(func.count(), func.min(RateEvent.created_at)).where(*same_key))).one()
    if count >= rule.limit:
        await db.commit()
        raise RateLimited(_minutes_until(oldest + rule.window, now))
    db.add(RateEvent(bucket=rule.bucket, key_hash=key_hash, created_at=now))
    await db.commit()


async def _purge_stale(db: AsyncSession, now: datetime) -> None:
    stale = (
        select(RateEvent.id)
        .where(RateEvent.created_at <= now - LONGEST_WINDOW)
        .limit(PURGE_BATCH)
        .with_for_update(skip_locked=True)
    )
    await db.execute(delete(RateEvent).where(RateEvent.id.in_(stale.scalar_subquery())))


def _minutes_until(moment: datetime, now: datetime) -> int:
    return max(1, math.ceil((moment - now).total_seconds() / 60))
