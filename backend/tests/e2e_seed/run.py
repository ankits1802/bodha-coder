from __future__ import annotations

import secrets

from app.core.config import get_settings
from tests.e2e_seed.accounts import Account, create_hq_account, enrol_two_step, hq_caller, practice_caller
from tests.e2e_seed.api import Api, Caller, SeedFailed
from tests.e2e_seed.practices import (
    HQ_TOUR,
    PRACTICE_TOUR,
    Practice,
    Provider,
    add_practice_for,
    add_provider,
    create_practice,
    invite,
    skip_tour,
)

__all__ = ["EMAIL_DOMAIN", "SeedRun", "refuse_production"]

EMAIL_DOMAIN = "e2e.example.com"
MARKER_BYTES = 3
ADMIN_NAME = "Avery Admin"


def refuse_production() -> None:
    settings = get_settings()
    if settings.app_environment == "production":
        raise SeedFailed("the synthetic seed never runs against APP_ENVIRONMENT=production")
    if settings.gemini_backend != "demo":
        raise SeedFailed("the synthetic seed needs GEMINI_BACKEND=demo")


class SeedRun:
    def __init__(self, api: Api, tour_version: int) -> None:
        self.api = api
        self.tour_version = tour_version
        self.marker = secrets.token_hex(MARKER_BYTES)
        self._hq: Caller | None = None

    def email(self, local: str) -> str:
        return f"{local}-{self.marker}@{EMAIL_DOMAIN}"

    def named(self, name: str) -> str:
        return f"{name} {self.marker.upper()}"

    async def hq(self) -> Caller:
        if self._hq is None:
            account = await create_hq_account("Seed HQ", self.email("seed-hq"), two_step=False)
            self._hq = await hq_caller(account)
        return self._hq

    async def hq_person(self, name: str) -> Account:
        account = await create_hq_account(name, self.email("hq"), two_step=True)
        await skip_tour(self.api, await hq_caller(account), tour=HQ_TOUR, version=self.tour_version)
        return account

    async def practice(self, name: str, *, admin_mailbox: str = "admin") -> Practice:
        created = await create_practice(
            self.api,
            await self.hq(),
            name=self.named(name),
            admin_name=ADMIN_NAME,
            admin_email=self.email(admin_mailbox),
        )
        admin = await enrol_two_step(created.admin)
        await self.toured(admin, created.id)
        return Practice(created.id, created.name, admin)

    async def second_practice(self, name: str, admin: Account) -> Practice:
        practice = await add_practice_for(self.api, await self.hq(), name=self.named(name), admin=admin)
        await self.toured(admin, practice.id)
        return practice

    async def member(self, practice: Practice, *, name: str, role: str, two_step: bool = False) -> Account:
        local = name.split()[0].lower()
        account = await invite(self.api, practice, name=name, email=self.email(f"{role}-{local}"), role=role)
        account = await enrol_two_step(account) if two_step else account
        await self.toured(account, practice.id)
        return account

    async def provider(self, practice: Practice, *, name: str, npi: str) -> Provider:
        local = name.split()[-1].lower()
        return await add_provider(self.api, practice, name=name, npi=npi, email=self.email(f"dr-{local}"))

    async def toured(self, account: Account, practice_id: str) -> None:
        caller = await practice_caller(account, practice_id)
        await skip_tour(self.api, caller, tour=PRACTICE_TOUR, version=self.tour_version)
