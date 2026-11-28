from __future__ import annotations

import argparse
import asyncio
import json
import sys
from typing import Any

from app.api.wiring import REFRESH_COOKIE, REFRESH_PATH
from app.core.db import SessionFactory, engine
from app.core.deps import Client, practice_access
from app.models import User
from app.services.auth import start_session
from tests.e2e_seed.run import refuse_production

__all__ = ["open_sessions"]

SWEEP_METHOD = "the synthetic browser sweep"
PRACTICE_SEPARATOR = ":"


async def open_sessions(people: list[tuple[str, str | None]]) -> list[str]:
    tokens = []
    async with SessionFactory() as db:
        for user_id, practice_id in people:
            user = await db.get_one(User, user_id)
            standing = await practice_access(db, user, practice_id)
            opened = await start_session(db, user, standing, method=SWEEP_METHOD, client=Client(None, None))
            tokens.append(opened.refresh)
    return tokens


def person(value: str) -> tuple[str, str | None]:
    user_id, _, practice_id = value.partition(PRACTICE_SEPARATOR)
    return user_id, practice_id or None


async def opened(people: list[tuple[str, str | None]]) -> dict[str, Any]:
    refuse_production()
    try:
        return {"cookie": {"name": REFRESH_COOKIE, "path": REFRESH_PATH}, "tokens": await open_sessions(people)}
    finally:
        await engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m tests.e2e_seed.sessions")
    parser.add_argument("people", nargs="+", type=person)
    chosen = parser.parse_args()
    sys.stdout.write(json.dumps(asyncio.run(opened(chosen.people))) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
