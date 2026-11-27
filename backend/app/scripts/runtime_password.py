from __future__ import annotations

import asyncio
import os
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings
from app.core.role_password import RUNTIME_ROLE, scram_verifier

PASSWORD_VARIABLE = "RUNTIME_DATABASE_PASSWORD"


async def set_runtime_password() -> str:
    password = os.environ.get(PASSWORD_VARIABLE, "")
    if not password:
        raise SystemExit(f"set {PASSWORD_VARIABLE}")
    engine = create_async_engine(get_settings().migration_url)
    try:
        async with engine.begin() as connection:
            found = await connection.scalar(
                text("SELECT 1 FROM pg_roles WHERE rolname = :name"), {"name": RUNTIME_ROLE}
            )
            if not found:
                raise SystemExit(f"{RUNTIME_ROLE} does not exist yet; run the migrations first")
            await connection.execute(text(f"ALTER ROLE {RUNTIME_ROLE} PASSWORD '{scram_verifier(password)}'"))
    finally:
        await engine.dispose()
    return f"{RUNTIME_ROLE} password set"


if __name__ == "__main__":
    sys.stdout.write(asyncio.run(set_runtime_password()) + "\n")
