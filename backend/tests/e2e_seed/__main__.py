from __future__ import annotations

import argparse
import asyncio
import json
import sys

from app.core.db import engine
from tests.e2e_seed.api import Api
from tests.e2e_seed.run import SeedRun, refuse_production
from tests.e2e_seed.scenarios import SCENARIOS


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="python -m tests.e2e_seed")
    parser.add_argument("scenario", choices=sorted(SCENARIOS))
    parser.add_argument("--tour-version", type=int, required=True)
    return parser.parse_args()


async def seeded(scenario: str, tour_version: int) -> dict:
    refuse_production()
    try:
        async with Api.client() as client:
            return await SCENARIOS[scenario](SeedRun(Api(client), tour_version))
    finally:
        await engine.dispose()


def main() -> int:
    chosen = arguments()
    sys.stdout.write(json.dumps(asyncio.run(seeded(chosen.scenario, chosen.tour_version))) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
