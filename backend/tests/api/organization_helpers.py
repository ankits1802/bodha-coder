from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy import select

from app.core.db import SessionFactory
from app.models import DomainClaim, DomainJoinRequest, Organization, Practice
from tests.builders import Harness, practice_with_provider, sign_in
from tests.builders import Practice as BuiltPractice

ORG_ADMIN = "admin@lakeside.example.com"
RIVERBEND_ADMIN = "admin@riverbend.example.com"
GROUP_NAME = "Acme Health"
DOMAIN = "lakeside.example.com"
JOIN_LINK = re.compile(r"/sign-up/join#(\S+)$")


@dataclass
class Group:
    id: str
    hq: dict[str, str]
    lakeside: BuiltPractice
    riverbend: BuiltPractice


async def organization_of_two(harness: Harness, *, plan: str = "essentials") -> Group:
    lakeside = await practice_with_provider(harness)
    riverbend = await practice_with_provider(harness, name="Riverbend", admin_email=RIVERBEND_ADMIN)
    hq = await sign_in(harness.client, "hq-admin@lakeside.example.com", secret_box=lakeside.secrets)
    created = await harness.client.post("/api/hq/organizations", headers=hq, json={"name": GROUP_NAME, "plan": plan})
    assert created.status_code == 200, created.text
    group = Group(created.json()["id"], hq, lakeside, riverbend)
    for practice in (lakeside, riverbend):
        attached = await harness.client.post(
            f"/api/hq/organizations/{group.id}/practices", headers=hq, json={"practice_id": practice.id}
        )
        assert attached.status_code == 204, attached.text
    added = await harness.client.post(
        f"/api/hq/organizations/{group.id}/admins", headers=hq, json={"email": ORG_ADMIN, "reason": "Group office"}
    )
    assert added.status_code == 200, added.text
    return group


def organization_path(group: Group, suffix: str = "") -> str:
    return f"/api/organizations/{group.id}{suffix}"


async def combine(harness: Harness, group: Group, practice_id: str, *, combined: bool = True) -> None:
    response = await harness.client.put(
        organization_path(group, f"/practices/{practice_id}/billing"),
        headers=group.lakeside.admin,
        json={"combined": combined},
    )
    assert response.status_code == 204, response.text


async def stored_practice(practice_id: str) -> Practice:
    async with SessionFactory() as db:
        return await db.get_one(Practice, practice_id)


async def stored_organization(organization_id: str) -> Organization:
    async with SessionFactory() as db:
        return await db.get_one(Organization, organization_id)


async def claim_rows(domain: str = DOMAIN) -> list[DomainClaim]:
    async with SessionFactory() as db:
        rows = await db.scalars(
            select(DomainClaim).where(DomainClaim.domain == domain).order_by(DomainClaim.created_at)
        )
        return list(rows.all())


async def join_rows(practice_id: str) -> list[DomainJoinRequest]:
    async with SessionFactory() as db:
        rows = await db.scalars(
            select(DomainJoinRequest)
            .where(DomainJoinRequest.practice_id == practice_id)
            .order_by(DomainJoinRequest.created_at)
        )
        return list(rows.all())


async def verified_domain(harness: Harness, admin: dict[str, str], *, mode: str, role: str = "viewer") -> str:
    claimed = await harness.client.post("/api/practice/domains", headers=admin, json={"domain": DOMAIN})
    assert claimed.status_code == 200, claimed.text
    claim_id = claimed.json()["id"]
    listed = (await harness.client.get("/api/practice/domains", headers=admin)).json()
    harness.dns.records[DOMAIN] = [next(row["txt_record"] for row in listed if row["id"] == claim_id)]
    checked = await harness.client.post(f"/api/practice/domains/{claim_id}/check", headers=admin)
    assert checked.status_code == 204, checked.text
    joined = await harness.client.put(
        f"/api/practice/domains/{claim_id}/join", headers=admin, json={"mode": mode, "role": role}
    )
    assert joined.status_code == 204, joined.text
    return claim_id


def join_token(harness: Harness, email: str) -> str:
    to, body = harness.messenger.sent[-1]
    found = JOIN_LINK.search(body)
    assert to == email and found, body
    return found.group(1)
