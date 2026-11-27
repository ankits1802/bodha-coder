from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Actor
from app.core.errors import Conflict, Invalid, NotFound
from app.models import Practice, new_id
from app.services.audit_log import record_activity

__all__ = ["PLAN_TYPES", "add_payer", "change_payer", "has_active_payer", "payer_list", "remove_payer"]

SECTION = "payers"
LIST_KEY = "list"
PLAN_TYPES = ("commercial", "medicare", "medicare_advantage", "medicaid", "other")
PAYER_ID = re.compile(r"^[A-Z0-9-]{2,15}$")
MAX_PAYERS = 200


def payer_list(practice: Practice) -> list[dict[str, Any]]:
    return list((practice.setup.get(SECTION) or {}).get(LIST_KEY, []))


def has_active_payer(practice: Practice) -> bool:
    return any(payer.get("active") for payer in payer_list(practice))


async def add_payer(db: AsyncSession, actor: Actor, values: Mapping[str, Any]) -> dict[str, Any]:
    practice = await _locked_practice(db, actor)
    payers = payer_list(practice)
    if len(payers) >= MAX_PAYERS:
        raise Conflict(f"a practice can list at most {MAX_PAYERS} payers")
    payer = {"id": new_id(), **_validated(values, payers)}
    _store(practice, [*payers, payer])
    record_activity(db, actor, "payer added", practice_id=practice.id, detail=payer["name"])
    await db.commit()
    return payer


async def change_payer(db: AsyncSession, actor: Actor, payer_key: str, values: Mapping[str, Any]) -> dict[str, Any]:
    practice = await _locked_practice(db, actor)
    payers = payer_list(practice)
    _find(payers, payer_key)
    others = [payer for payer in payers if payer["id"] != payer_key]
    changed = {"id": payer_key, **_validated(values, others)}
    _store(practice, [changed if payer["id"] == payer_key else payer for payer in payers])
    record_activity(db, actor, "payer changed", practice_id=practice.id, detail=changed["name"])
    await db.commit()
    return changed


async def remove_payer(db: AsyncSession, actor: Actor, payer_key: str) -> None:
    practice = await _locked_practice(db, actor)
    payers = payer_list(practice)
    removed = _find(payers, payer_key)
    _store(practice, [payer for payer in payers if payer["id"] != payer_key])
    record_activity(db, actor, "payer removed", practice_id=practice.id, detail=removed["name"])
    await db.commit()


async def _locked_practice(db: AsyncSession, actor: Actor) -> Practice:
    practice = await db.get(Practice, actor.practice_id, with_for_update=True, populate_existing=True)
    if practice is None:
        raise NotFound("practice not found")
    return practice


def _find(payers: list[dict[str, Any]], payer_key: str) -> dict[str, Any]:
    for payer in payers:
        if payer["id"] == payer_key:
            return payer
    raise NotFound("payer not found")


def _validated(values: Mapping[str, Any], others: list[dict[str, Any]]) -> dict[str, Any]:
    name = str(values.get("name") or "").strip()
    payer_id = str(values.get("payer_id") or "").strip().upper() or None
    plan_type = values.get("plan_type")
    if not name or len(name) > 120:
        raise Invalid("each payer needs a name of at most 120 characters")
    if payer_id and PAYER_ID.fullmatch(payer_id) is None:
        raise Invalid(f"{payer_id} is not a payer ID (2 to 15 letters, digits or hyphens)")
    if plan_type not in PLAN_TYPES:
        raise Invalid(f"plan type must be one of: {', '.join(PLAN_TYPES)}")
    if any(other["name"].lower() == name.lower() for other in others):
        raise Conflict(f"{name} is already in the payer list")
    return {"name": name, "payer_id": payer_id, "plan_type": plan_type, "active": bool(values.get("active", True))}


def _store(practice: Practice, payers: list[dict[str, Any]]) -> None:
    section = dict(practice.setup.get(SECTION) or {})
    practice.setup = {**practice.setup, SECTION: {**section, LIST_KEY: payers}}
