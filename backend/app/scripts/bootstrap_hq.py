from __future__ import annotations

import asyncio
import sys

from sqlalchemy import select

from app.core.config import get_settings
from app.core.db import SessionFactory
from app.core.realms import account_space
from app.core.roles import HQ_ROLE
from app.core.security import PASSWORD_MIN_LENGTH, hash_password
from app.models import HQ_REALM, User


async def bootstrap() -> str:
    settings = get_settings()
    email, password = settings.bootstrap_hq_email, settings.bootstrap_hq_password
    if not email or not password or len(password) < PASSWORD_MIN_LENGTH:
        raise SystemExit("set BOOTSTRAP_HQ_EMAIL and a BOOTSTRAP_HQ_PASSWORD of at least 10 characters")
    address = email.strip().lower()
    async with SessionFactory() as db:
        if await db.scalar(select(User.id).where(User.realm == HQ_REALM)):
            return "an HQ account already exists; nothing changed"
        if await db.scalar(select(User.id).where(User.email == address, User.realm.in_(account_space(HQ_REALM)))):
            raise SystemExit("BOOTSTRAP_HQ_EMAIL already belongs to a practice account; choose another email")
        db.add(
            User(
                email=address,
                name="Bodha Admin",
                role=HQ_ROLE,
                status="active",
                password_hash=hash_password(password),
            )
        )
        await db.commit()
    return "HQ account created; set up two-step verification at first sign-in"


if __name__ == "__main__":
    sys.stdout.write(asyncio.run(bootstrap()) + "\n")
