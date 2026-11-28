from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from app.core.calendar import today_in, zone_named
from app.core.db import SessionFactory
from app.models import Practice as PracticeRow
from tests.e2e_seed.accounts import Account, accept_invite, practice_caller
from tests.e2e_seed.api import Api, Caller

__all__ = [
    "HQ_TOUR",
    "PLAN",
    "PRACTICE_TOUR",
    "VARGA_NPI",
    "Practice",
    "Provider",
    "add_payer",
    "add_practice_for",
    "add_provider",
    "create_practice",
    "end_plan",
    "invite",
    "send_invite",
    "skip_tour",
]

PLAN = "professional"
SEATS = 10
TIME_ZONE = "America/Chicago"
PRACTICE_TOUR = "practice"
HQ_TOUR = "hq"
VARGA_NPI = "1234567893"


@dataclass(frozen=True)
class Practice:
    id: str
    name: str
    admin: Account


@dataclass(frozen=True)
class Provider:
    id: str
    name: str
    npi: str
    email: str

    def view(self) -> dict[str, Any]:
        return {"id": self.id, "name": self.name, "npi": self.npi, "email": self.email}


async def create_practice(api: Api, hq: Caller, *, name: str, admin_name: str, admin_email: str) -> Practice:
    body = {"name": name, "admin_name": admin_name, "admin_email": admin_email, "plan": PLAN, "seats": SEATS}
    created = await api.send(hq, "POST", "/api/hq/practices", json={**body, "time_zone": TIME_ZONE})
    admin = await accept_invite(api, name=admin_name, email=admin_email, role="admin")
    return Practice(created["id"], name, admin)


async def add_practice_for(api: Api, hq: Caller, *, name: str, admin: Account) -> Practice:
    body = {"name": name, "admin_name": admin.name, "admin_email": admin.email, "plan": PLAN, "seats": SEATS}
    created = await api.send(hq, "POST", "/api/hq/practices", json={**body, "time_zone": TIME_ZONE})
    return Practice(created["id"], name, admin)


async def send_invite(api: Api, practice: Practice, *, name: str, email: str, role: str) -> None:
    admin = await practice_caller(practice.admin, practice.id)
    await api.send(admin, "POST", "/api/team", json={"name": name, "email": email, "role": role})


async def invite(api: Api, practice: Practice, *, name: str, email: str, role: str) -> Account:
    await send_invite(api, practice, name=name, email=email, role=role)
    return await accept_invite(api, name=name, email=email, role=role)


async def add_provider(api: Api, practice: Practice, *, name: str, npi: str, email: str) -> Provider:
    admin = await practice_caller(practice.admin, practice.id)
    body = {"name": name, "credential": "MD", "specialty": "Internal medicine", "npi": npi, "place_code": "11"}
    created = await api.send(admin, "POST", "/api/providers", json={**body, "email": email, "channel": "email"})
    return Provider(created["id"], name, npi, email)


async def add_payer(api: Api, practice: Practice, *, name: str, payer_id: str, plan_type: str) -> None:
    admin = await practice_caller(practice.admin, practice.id)
    await api.send(
        admin, "POST", "/api/practice/payers", json={"name": name, "payer_id": payer_id, "plan_type": plan_type}
    )


async def skip_tour(api: Api, caller: Caller, *, tour: str, version: int) -> None:
    await api.send(caller, "PUT", f"/api/account/tours/{tour}", json={"version": version, "outcome": "skipped"})


async def end_plan(practice: Practice) -> None:
    async with SessionFactory() as db:
        row = await db.get_one(PracticeRow, practice.id)
        row.renews_on = today_in(zone_named(row.time_zone)) - timedelta(days=1)
        await db.commit()
