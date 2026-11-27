from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.calendar import zone_named
from app.models import Practice, User

SIGNUP_SOURCES = ("self", "hq")


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


def normal_email(email: str) -> str:
    return email.strip().lower()


async def email_in_use(db: AsyncSession, email: str) -> bool:
    return await db.scalar(select(User.id).where(User.email == normal_email(email))) is not None


async def add_practice_with_admin(db: AsyncSession, draft: PracticeDraft, admin: AdminDraft) -> NewPractice:
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
    user = User(
        practice_id=practice.id,
        email=normal_email(admin.email),
        name=admin.name.strip(),
        role="admin",
        status=admin.status,
    )
    db.add(user)
    await db.flush()
    return NewPractice(practice, user)


def signup_source(practice: Practice) -> str | None:
    source = (practice.signup or {}).get("source")
    return source if source in SIGNUP_SOURCES else None
