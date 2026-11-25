from __future__ import annotations

import asyncio
import sys

from sqlalchemy import select

from app.core.config import get_settings
from app.core.db import SessionFactory
from app.core.security import PASSWORD_MIN_LENGTH, hash_password
from app.models import User


async def bootstrap() -> str:
    settings = get_settings()
    email, password = settings.bootstrap_hq_email, settings.bootstrap_hq_password
    if not email or not password or len(password) < PASSWORD_MIN_LENGTH:
        raise SystemExit("set BOOTSTRAP_HQ_EMAIL and a BOOTSTRAP_HQ_PASSWORD of at least 10 characters")
    async with SessionFactory() as db:
        if await db.scalar(select(User.id).where(User.role == "hq")):
            return "an HQ account already exists; nothing changed"
        db.add(
            User(
                email=email.strip().lower(),
                name="Bodha Admin",
                role="hq",
                status="active",
                password_hash=hash_password(password),
            )
        )
        await db.commit()
    return "HQ account created; set up two-step verification at first sign-in"


if __name__ == "__main__":
    sys.stdout.write(asyncio.run(bootstrap()) + "\n")
