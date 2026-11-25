from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.messenger import Messenger
from app.core.config import get_settings
from app.models import User
from app.services.auth import TOKEN_HOURS, issue_user_token
from app.services.rate_limits import FORGOT_PER_EMAIL, FORGOT_PER_IP, hit

RESETTABLE_STATUSES = ("active", "invited")


async def count_reset_request(db: AsyncSession, email: str, *, ip: str | None) -> None:
    await hit(db, FORGOT_PER_EMAIL, email.strip().lower())
    await hit(db, FORGOT_PER_IP, ip)


async def send_reset_for_email(db: AsyncSession, messenger: Messenger, email: str) -> None:
    user = await db.scalar(select(User).where(User.email == email.strip().lower()))
    if user is None or user.status not in RESETTABLE_STATUSES:
        return
    await send_reset_email(db, messenger, user)


async def send_reset_email(db: AsyncSession, messenger: Messenger, user: User) -> None:
    token = await issue_user_token(db, user, "reset")
    await db.commit()
    link = f"{get_settings().app_url}/set-password#{token}"
    hours = TOKEN_HOURS["reset"]
    await messenger.email(
        user.email,
        subject="Reset your Bodha Coder password",
        body=(
            f"{user.name}, a password reset was asked for your Bodha Coder account. "
            f"The link works once, for {hours} hour{'s' if hours != 1 else ''}. Reset your password: {link}"
        ),
    )
