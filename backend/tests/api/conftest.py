from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from cryptography.fernet import Fernet
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.adapters.billing_providers import PROVIDER_NAMES as BILLING_NAMES
from app.adapters.development_signer import DevelopmentRecordSigner
from app.adapters.oidc_providers import PROVIDER_NAMES
from app.core.config import get_settings
from app.core.db import SessionFactory
from app.main import app
from app.models import Base
from tests.builders import ADMIN_SITE, Harness, maintenance
from tests.ehr_fakes import FakeEhr
from tests.fakes import (
    FakeBillingProvider,
    FakeFileLink,
    FakeImageModel,
    FakeMessenger,
    FakeProvider,
    FakeStore,
    FakeTxtResolver,
)

BACKEND = Path(__file__).resolve().parents[2]
KEPT_TABLES = ("places_of_service",)


@pytest.fixture(scope="session", autouse=True)
def schema() -> None:
    command.upgrade(Config(str(BACKEND / "alembic.ini")), "head")


@pytest.fixture(autouse=True)
async def clean_tables() -> None:
    names = ", ".join(table.name for table in Base.metadata.sorted_tables if table.name not in KEPT_TABLES)
    async with SessionFactory() as db:
        await maintenance(db)
        await db.execute(text(f"TRUNCATE {names} RESTART IDENTITY CASCADE"))
        await db.commit()


@pytest.fixture
def clearinghouse_key(monkeypatch) -> str:
    key = Fernet.generate_key().decode()
    monkeypatch.setattr(get_settings(), "clearinghouse_encryption_key", key)
    return key


@pytest.fixture
def two_hosts(monkeypatch) -> str:
    monkeypatch.setattr(get_settings(), "admin_url", ADMIN_SITE)
    return ADMIN_SITE


@pytest.fixture
async def harness(icd_catalog) -> AsyncIterator[Harness]:
    store, messenger, image_model = FakeStore(), FakeMessenger(), FakeImageModel()
    providers = {name: FakeProvider(name) for name in PROVIDER_NAMES}
    app.state.store, app.state.messenger, app.state.icd = store, messenger, icd_catalog
    app.state.signer, app.state.image_model = DevelopmentRecordSigner(), image_model
    app.state.identity_providers = providers
    billing = {name: FakeBillingProvider(name) for name in BILLING_NAMES}
    app.state.billing_providers = billing
    dns, link = FakeTxtResolver(), FakeFileLink()
    app.state.txt_resolver, app.state.file_link = dns, link
    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://app.test") as client:
        yield Harness(client, store, messenger, providers, billing, image_model, dns, link)


@pytest.fixture
def ehr_key(monkeypatch) -> str:
    key = Fernet.generate_key().decode()
    monkeypatch.setattr(get_settings(), "ehr_key_encryption_key", key)
    return key


@pytest.fixture
def ehr(harness: Harness, ehr_key: str) -> FakeEhr:
    fake = FakeEhr()
    app.state.outbound = fake.outbound()
    return fake
