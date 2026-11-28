from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from tests.e2e_seed.accounts import Account, accept_invite, practice_caller
from tests.e2e_seed.api import Api, Caller

__all__ = [
    "HQ_TOUR",
    "PLAN",
    "PRACTICE_TOUR",
    "Practice",
    "Provider",
    "add_practice_for",
    "add_provider",
    "create_practice",
    "invite",
    "skip_tour",
]

PLAN = "professional"
SEATS = 10
TIME_ZONE = "America/Chicago"
PRACTICE_TOUR = "practice"
HQ_TOUR = "hq"


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


async def invite(api: Api, practice: Practice, *, name: str, email: str, role: str) -> Account:
    admin = await practice_caller(practice.admin, practice.id)
    await api.send(admin, "POST", "/api/team", json={"name": name, "email": email, "role": role})
    return await accept_invite(api, name=name, email=email, role=role)


async def add_provider(api: Api, practice: Practice, *, name: str, npi: str, email: str) -> Provider:
    admin = await practice_caller(practice.admin, practice.id)
    body = {"name": name, "credential": "MD", "specialty": "Internal medicine", "npi": npi, "place_code": "11"}
    created = await api.send(admin, "POST", "/api/providers", json={**body, "email": email, "channel": "email"})
    return Provider(created["id"], name, npi, email)


async def skip_tour(api: Api, caller: Caller, *, tour: str, version: int) -> None:
    await api.send(caller, "PUT", f"/api/account/tours/{tour}", json={"version": version, "outcome": "skipped"})
