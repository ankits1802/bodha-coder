from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Actor
from app.core.errors import Conflict, Invalid, NotFound
from app.models import Provider, QueueView
from app.services.worklists import DUE_SORT

__all__ = [
    "BUILTIN_BY_ROLE",
    "BUILTIN_KEYS",
    "MAX_SAVED_VIEWS",
    "builtin_views",
    "delete_view",
    "queue_views",
    "save_view",
    "view_filters",
]

MAX_SAVED_VIEWS = 20
BUILTIN: dict[str, dict[str, Any]] = {
    "my_work": {"assigned": "me"},
    "questions_to_send": {"lane": "provider", "reason": "questions"},
    "unassigned": {"assigned": "none"},
    "overdue": {"overdue": True},
    "flagged": {"lane": "compliance", "reason": "flagged"},
}
BUILTIN_KEYS = tuple(BUILTIN)
BUILTIN_BY_ROLE: dict[str, tuple[str, ...]] = {
    "admin": ("unassigned", "overdue"),
    "coder": ("my_work",),
    "cdi": ("questions_to_send",),
    "compliance": ("flagged",),
}


def view_filters(stored: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "lane": stored.get("lane"),
        "reason": stored.get("reason"),
        "assigned": stored.get("assigned"),
        "provider_id": stored.get("provider_id"),
        "overdue": bool(stored.get("overdue", False)),
        "sort": stored.get("sort") or DUE_SORT,
    }


def builtin_views(role: str) -> list[dict[str, Any]]:
    return [{"key": key, "filters": view_filters(BUILTIN[key])} for key in BUILTIN_BY_ROLE.get(role, ())]


async def queue_views(db: AsyncSession, actor: Actor) -> dict[str, Any]:
    rows = await db.scalars(select(QueueView).where(*_mine(actor)).order_by(QueueView.name, QueueView.id))
    return {"builtin": builtin_views(actor.role), "saved": [_saved(row) for row in rows]}


async def save_view(db: AsyncSession, actor: Actor, name: str, filters: Mapping[str, Any]) -> dict[str, Any]:
    await _check_provider(db, actor, filters.get("provider_id"))
    held = await db.scalar(select(func.count()).select_from(QueueView).where(*_mine(actor))) or 0
    if held >= MAX_SAVED_VIEWS:
        raise Conflict(f"keep at most {MAX_SAVED_VIEWS} saved views")
    same_name = await db.scalar(select(QueueView.id).where(*_mine(actor), func.lower(QueueView.name) == name.lower()))
    if same_name is not None:
        raise Conflict("you already have a view with that name")
    row = QueueView(user_id=actor.user.id, practice_id=actor.practice_id, name=name, filters=view_filters(filters))
    db.add(row)
    await db.commit()
    return _saved(row)


async def delete_view(db: AsyncSession, actor: Actor, view_id: str) -> None:
    row = await db.get(QueueView, view_id)
    if row is None or row.user_id != actor.user.id or row.practice_id != actor.practice_id:
        raise NotFound("view not found")
    await db.delete(row)
    await db.commit()


async def _check_provider(db: AsyncSession, actor: Actor, provider_id: str | None) -> None:
    if provider_id is None:
        return
    provider = await db.get(Provider, provider_id)
    if provider is None or provider.practice_id != actor.practice_id:
        raise Invalid("choose a provider of this practice")


def _mine(actor: Actor) -> tuple[Any, ...]:
    return QueueView.user_id == actor.user.id, QueueView.practice_id == actor.practice_id


def _saved(row: QueueView) -> dict[str, Any]:
    return {"id": row.id, "name": row.name, "filters": view_filters(row.filters)}
