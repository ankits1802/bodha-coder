from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.core.db import SessionFactory
from app.main import app
from app.models import Base
from tests.builders import Harness
from tests.fakes import FakeGoogle, FakeMessenger, FakeStore

BACKEND = Path(__file__).resolve().parents[2]
KEPT_TABLES = ("places_of_service",)


@pytest.fixture(scope="session", autouse=True)
def schema() -> None:
    command.upgrade(Config(str(BACKEND / "alembic.ini")), "head")


@pytest.fixture(autouse=True)
async def clean_tables() -> None:
    names = ", ".join(table.name for table in Base.metadata.sorted_tables if table.name not in KEPT_TABLES)
    async with SessionFactory() as db:
        await db.execute(text(f"TRUNCATE {names} RESTART IDENTITY CASCADE"))
        await db.commit()


@pytest.fixture
async def harness(icd_catalog) -> AsyncIterator[Harness]:
    store, messenger, google = FakeStore(), FakeMessenger(), FakeGoogle()
    app.state.store, app.state.messenger, app.state.icd, app.state.google = store, messenger, icd_catalog, google
    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://app.test") as client:
        yield Harness(client, store, messenger, google)
