from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFound
from app.core.text_search import LIKE_ESCAPE, contains_pattern, search_term
from app.models import (
    PRACTICE_REALM,
    Note,
    Organization,
    PlaceOfService,
    Practice,
    PracticeMembership,
    Provider,
    User,
)
from app.services.hq import practice_row
from app.services.memberships import BLOCKED, LIVE

__all__ = ["HQ_SEARCH_LIMIT", "hq_search", "practice_page", "practice_people", "practice_places"]

HQ_SEARCH_LIMIT = 20


async def practice_page(db: AsyncSession, practice_id: str) -> dict[str, Any]:
    return {"practice": await practice_row(db, practice_id), "places": await practice_places(db, practice_id)}


async def practice_places(db: AsyncSession, practice_id: str) -> list[dict[str, Any]]:
    providers = await _counts(db, Provider.place_code, Provider.practice_id == practice_id, Provider.active)
    notes = await _counts(db, Note.place_code, Note.practice_id == practice_id)
    codes = sorted({*providers, *notes})
    known = {
        place.code: place for place in await db.scalars(select(PlaceOfService).where(PlaceOfService.code.in_(codes)))
    }
    return [
        {
            "code": code,
            "name": known[code].name if code in known else code,
            "active": known[code].active if code in known else False,
            "providers": providers.get(code, 0),
            "notes": notes.get(code, 0),
        }
        for code in codes
    ]


async def practice_people(db: AsyncSession, practice_id: str) -> list[dict[str, Any]]:
    if await db.get(Practice, practice_id) is None:
        raise NotFound("practice not found")
    rows = await db.execute(
        select(User, PracticeMembership)
        .join(PracticeMembership, PracticeMembership.user_id == User.id)
        .where(PracticeMembership.practice_id == practice_id, LIVE)
        .order_by(User.name, User.id)
    )
    return [
        {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": membership.role,
            "status": BLOCKED if user.status == BLOCKED else membership.status,
            "mfa_enabled": user.mfa_enabled,
            "last_active_at": user.last_active_at.isoformat() if user.last_active_at else None,
        }
        for user, membership in rows.tuples()
    ]


async def hq_search(db: AsyncSession, text: str) -> dict[str, Any]:
    pattern = contains_pattern(search_term(text))
    practices = await db.execute(
        select(Practice.id, Practice.name, Practice.status)
        .where(Practice.name.ilike(pattern, escape=LIKE_ESCAPE))
        .order_by(Practice.name, Practice.id)
        .limit(HQ_SEARCH_LIMIT)
    )
    people = await db.scalars(
        select(User)
        .where(
            User.realm == PRACTICE_REALM,
            or_(User.email.ilike(pattern, escape=LIKE_ESCAPE), User.name.ilike(pattern, escape=LIKE_ESCAPE)),
        )
        .order_by(User.email, User.id)
        .limit(HQ_SEARCH_LIMIT)
    )
    found = list(people.all())
    places = await _memberships_of(db, [user.id for user in found])
    groups = await db.execute(
        select(Organization.id, Organization.name, Organization.status)
        .where(Organization.name.ilike(pattern, escape=LIKE_ESCAPE))
        .order_by(Organization.name, Organization.id)
        .limit(HQ_SEARCH_LIMIT)
    )
    return {
        "organizations": [{"id": row.id, "name": row.name, "status": row.status} for row in groups],
        "practices": [{"id": row.id, "name": row.name, "status": row.status} for row in practices],
        "people": [
            {"id": user.id, "name": user.name, "email": user.email, "practices": places.get(user.id, [])}
            for user in found
        ],
        "limit": HQ_SEARCH_LIMIT,
    }


async def _memberships_of(db: AsyncSession, user_ids: list[str]) -> dict[str, list[dict[str, str]]]:
    if not user_ids:
        return {}
    rows = await db.execute(
        select(PracticeMembership.user_id, Practice.id, Practice.name, PracticeMembership.role)
        .join(Practice, Practice.id == PracticeMembership.practice_id)
        .where(PracticeMembership.user_id.in_(user_ids), LIVE)
        .order_by(Practice.name, Practice.id)
    )
    found: dict[str, list[dict[str, str]]] = defaultdict(list)
    for user_id, practice_id, name, role in rows.tuples():
        found[user_id].append({"id": practice_id, "name": name, "role": role})
    return found


async def _counts(db: AsyncSession, column: Any, *conditions: Any) -> dict[str, int]:
    rows = await db.execute(select(column, func.count()).where(column.is_not(None), *conditions).group_by(column))
    return {code: count for code, count in rows.tuples()}
