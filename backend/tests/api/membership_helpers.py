from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import select, update

from app.core.db import SessionFactory
from app.models import AuthEvent, Practice, PracticeMembership
from tests.builders import Harness, invite_member, practice_with_provider, sign_in
from tests.builders import Practice as BuiltPractice

REFRESH = {"domain": "app.test", "path": "/api/auth"}
SAM = "sam@lakeside.example.com"
RIVERBEND_ADMIN = "admin@riverbend.example.com"
ENDED_ON = date(2025, 12, 31)


@dataclass
class TwoPractices:
    lakeside: BuiltPractice
    riverbend: BuiltPractice
    sam_id: str


@dataclass
class Person:
    headers: dict[str, str]
    refresh: str


async def two_practices(harness: Harness, *, riverbend_role: str = "coder") -> TwoPractices:
    lakeside = await practice_with_provider(harness)
    sam_id = await invite_member(harness, lakeside, name="Sam Patel", email=SAM, role="coder")
    riverbend = await practice_with_provider(harness, name="Riverbend", admin_email=RIVERBEND_ADMIN)
    added = await harness.client.post(
        "/api/team", headers=riverbend.admin, json={"name": "Samuel", "email": SAM, "role": riverbend_role}
    )
    assert added.status_code == 200, added.text
    assert added.json()["id"] == sam_id
    return TwoPractices(lakeside, riverbend, sam_id)


async def signed_in(harness: Harness, email: str, secrets: dict[str, str] | None = None) -> Person:
    headers = await sign_in(harness.client, email, secret_box=secrets)
    return Person(headers, harness.client.cookies.get("bodha_refresh", **REFRESH))


async def switch(harness: Harness, person: Person, practice_id: str):
    harness.client.cookies.set("bodha_refresh", person.refresh, **REFRESH)
    return await harness.client.post("/api/auth/practice", headers=person.headers, json={"practice_id": practice_id})


def bearer(body: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {body['access_token']}"}


async def me(harness: Harness, headers: dict[str, str]) -> dict:
    response = await harness.client.get("/api/auth/me", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


async def access_log(harness: Harness, admin: dict[str, str]) -> list[dict]:
    response = await harness.client.get("/api/access-log", headers=admin)
    assert response.status_code == 200, response.text
    return response.json()["items"]


async def membership_of(user_id: str, practice_id: str) -> PracticeMembership:
    async with SessionFactory() as db:
        found = await db.scalar(
            select(PracticeMembership).where(
                PracticeMembership.user_id == user_id, PracticeMembership.practice_id == practice_id
            )
        )
        assert found is not None
        return found


async def end_plan(practice_id: str) -> None:
    async with SessionFactory() as db:
        await db.execute(update(Practice).where(Practice.id == practice_id).values(renews_on=ENDED_ON))
        await db.commit()


async def auth_events(kind: str) -> list[AuthEvent]:
    async with SessionFactory() as db:
        rows = await db.scalars(select(AuthEvent).where(AuthEvent.kind == kind).order_by(AuthEvent.created_at))
        return list(rows.all())
