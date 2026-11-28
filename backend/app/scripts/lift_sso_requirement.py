from __future__ import annotations

import asyncio
import sys

from app.core.db import SessionFactory
from app.core.errors import AppError
from app.services.sso_recovery import lift_requirement

USAGE = 'usage: python -m app.scripts.lift_sso_requirement <connection id> "<reason and ticket>"\n'


async def lift(connection_id: str, reason: str) -> tuple[int, str]:
    async with SessionFactory() as db:
        try:
            version = await lift_requirement(db, connection_id, reason=reason)
        except AppError as error:
            return 1, f"{connection_id}: {error.message}"
    return 0, f"{connection_id}: single sign-on no longer required (version {version})"


def main(arguments: list[str]) -> int:
    if len(arguments) != 2:
        sys.stderr.write(USAGE)
        return 2
    status, line = asyncio.run(lift(arguments[0], arguments[1]))
    (sys.stderr if status else sys.stdout).write(line + "\n")
    return status


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
