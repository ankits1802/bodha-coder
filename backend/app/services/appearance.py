from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User

__all__ = ["appearance_of", "save_appearance"]


def appearance_of(user: User) -> dict[str, str]:
    return {"theme": user.theme, "text_size": user.text_size, "reduce_motion": user.reduce_motion}


async def save_appearance(
    db: AsyncSession, user: User, *, theme: str, text_size: str, reduce_motion: str
) -> dict[str, str]:
    user.theme = theme
    user.text_size = text_size
    user.reduce_motion = reduce_motion
    await db.commit()
    return appearance_of(user)
