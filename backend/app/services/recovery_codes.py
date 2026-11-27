from __future__ import annotations

import secrets

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Client
from app.core.errors import Invalid
from app.core.security import digest
from app.models import RecoveryCode, User, utcnow
from app.services.auth_events import AuthEventFacts, record_auth_event
from app.services.rate_limits import MFA_PER_USER, hit
from app.services.two_step import accept_code

RECOVERY_CODE_COUNT = 10
CODE_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"
CODE_GROUPS = 4
GROUP_LENGTH = 4


async def replace_recovery_codes(db: AsyncSession, user: User) -> tuple[str, ...]:
    await clear_recovery_codes(db, user)
    codes = tuple(_new_code() for _ in range(RECOVERY_CODE_COUNT))
    db.add_all(RecoveryCode(user_id=user.id, code_hash=digest(_normalised(code))) for code in codes)
    return codes


async def clear_recovery_codes(db: AsyncSession, user: User) -> None:
    await db.execute(
        update(RecoveryCode)
        .where(RecoveryCode.user_id == user.id, RecoveryCode.used_at.is_(None))
        .values(used_at=utcnow())
        .execution_options(synchronize_session=False)
    )


async def use_recovery_code(db: AsyncSession, user: User, code: str) -> bool:
    used = await db.scalar(
        update(RecoveryCode)
        .where(
            RecoveryCode.user_id == user.id,
            RecoveryCode.code_hash == digest(_normalised(code)),
            RecoveryCode.used_at.is_(None),
        )
        .values(used_at=utcnow())
        .returning(RecoveryCode.id)
        .execution_options(synchronize_session=False)
    )
    return used is not None


async def remaining_recovery_codes(db: AsyncSession, user: User) -> int:
    count = await db.scalar(
        select(func.count())
        .select_from(RecoveryCode)
        .where(RecoveryCode.user_id == user.id, RecoveryCode.used_at.is_(None))
    )
    return count or 0


async def regenerate_recovery_codes(db: AsyncSession, user: User, code: str, *, client: Client) -> tuple[str, ...]:
    await hit(db, MFA_PER_USER, user.id)
    if not user.mfa_enabled or not accept_code(user, code):
        raise Invalid("that code is not correct")
    codes = await replace_recovery_codes(db, user)
    await record_auth_event(db, "recovery_codes_replaced", user, AuthEventFacts(client))
    await db.commit()
    return codes


def _new_code() -> str:
    return "-".join("".join(secrets.choice(CODE_ALPHABET) for _ in range(GROUP_LENGTH)) for _ in range(CODE_GROUPS))


def _normalised(code: str) -> str:
    return "".join(code.split()).replace("-", "").lower()
