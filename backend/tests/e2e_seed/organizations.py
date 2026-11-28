from __future__ import annotations

from dataclasses import dataclass

from tests.e2e_seed.accounts import Account
from tests.e2e_seed.api import Api, Caller
from tests.e2e_seed.practices import Practice

__all__ = ["Organization", "create_organization"]

ORGANIZATION_PLAN = "professional"
ADMIN_REASON = "Synthetic organization for browser journeys"


@dataclass(frozen=True)
class Organization:
    id: str
    name: str


async def create_organization(
    api: Api, hq: Caller, *, name: str, practices: list[Practice], admin: Account
) -> Organization:
    created = await api.send(hq, "POST", "/api/hq/organizations", json={"name": name, "plan": ORGANIZATION_PLAN})
    path = f"/api/hq/organizations/{created['id']}"
    for practice in practices:
        await api.send(hq, "POST", f"{path}/practices", json={"practice_id": practice.id})
    await api.send(hq, "POST", f"{path}/admins", json={"email": admin.email, "reason": ADMIN_REASON})
    return Organization(created["id"], name)
