from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.realms import account_space
from app.models import User

__all__ = ["account_by_email", "email_in_use", "normal_email"]


def normal_email(email: str) -> str:
    return email.strip().lower()


async def account_by_email(db: AsyncSession, email: str, realms: tuple[str, ...]) -> User | None:
    query = select(User).where(User.email == normal_email(email), User.realm.in_(realms)).limit(2)
    found = (await db.scalars(query)).all()
    return found[0] if len(found) == 1 else None


async def email_in_use(db: AsyncSession, email: str, realm: str) -> bool:
    query = select(User.id).where(User.email == normal_email(email), User.realm.in_(account_space(realm)))
    return await db.scalar(query.limit(1)) is not None
