from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.calendar import zone_named
from app.core.roles import ADMIN_ROLE
from app.models import Practice, PracticeMembership, User
from app.services.account_lookup import normal_email
from app.services.memberships import enrol

SIGNUP_SOURCES = ("self", "hq", "organization")


@dataclass(frozen=True)
class PracticeDraft:
    name: str
    plan: str
    status: str
    seats: int
    time_zone: str
    renews_on: date | None = None
    signup: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AdminDraft:
    name: str
    email: str
    status: str


@dataclass(frozen=True)
class NewPractice:
    practice: Practice
    admin: User
    membership: PracticeMembership


async def add_practice_with_admin(db: AsyncSession, draft: PracticeDraft, admin: AdminDraft) -> NewPractice:
    user = User(email=normal_email(admin.email), name=admin.name.strip(), role=ADMIN_ROLE, status=admin.status)
    db.add(user)
    await db.flush()
    return await add_practice_for_person(db, draft, user)


async def add_practice_for_person(db: AsyncSession, draft: PracticeDraft, person: User) -> NewPractice:
    practice = Practice(
        name=draft.name.strip(),
        plan=draft.plan,
        seats=draft.seats,
        status=draft.status,
        time_zone=zone_named(draft.time_zone).key,
        renews_on=draft.renews_on,
        signup=dict(draft.signup),
    )
    db.add(practice)
    await db.flush()
    membership = await enrol(db, person, practice.id, ADMIN_ROLE, invited_by=None)
    return NewPractice(practice, person, membership)


def signup_source(practice: Practice) -> str | None:
    source = (practice.signup or {}).get("source")
    return source if source in SIGNUP_SOURCES else None
