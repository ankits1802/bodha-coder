from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.messenger import Messenger
from app.core.realms import realm_url
from app.models import User
from app.services.account_lookup import account_by_email, normal_email
from app.services.auth import TOKEN_HOURS, issue_user_token
from app.services.rate_limits import FORGOT_PER_EMAIL, FORGOT_PER_IP, hit
from app.services.sso_policy import signs_in_with_sso

RESETTABLE_STATUSES = ("active", "invited")


async def count_reset_request(db: AsyncSession, email: str, *, ip: str | None) -> None:
    await hit(db, FORGOT_PER_EMAIL, normal_email(email))
    await hit(db, FORGOT_PER_IP, ip)


async def send_reset_for_email(db: AsyncSession, messenger: Messenger, email: str, realms: tuple[str, ...]) -> None:
    user = await account_by_email(db, email, realms)
    if user is None or user.status not in RESETTABLE_STATUSES or await signs_in_with_sso(db, user):
        return
    await send_reset_email(db, messenger, user)


async def send_reset_email(db: AsyncSession, messenger: Messenger, user: User) -> None:
    token = await issue_user_token(db, user, "reset")
    link = f"{realm_url(user.realm)}/set-password#{token}"
    await db.commit()
    hours = TOKEN_HOURS["reset"]
    await messenger.email(
        user.email,
        subject="Reset your Bodha Assure password",
        body=(
            f"{user.name}, a password reset was asked for your Bodha Assure account. "
            f"The link works once, for {hours} hour{'s' if hours != 1 else ''}. Reset your password: {link}"
        ),
    )
