from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Actor
from app.core.errors import Conflict
from app.models import Practice, Provider, utcnow
from app.services.audit_log import record_activity

__all__ = ["CHECKS_REVIEWED", "DISMISSED", "SECURITY_REVIEWED", "dismiss_first_run", "first_run_view", "mark_first_run"]

FIRST_RUN_KEY = "first_run"
CHECKS_REVIEWED = "checks"
SECURITY_REVIEWED = "security"
DISMISSED = "dismissed"
FIRST_RUN_STEPS = (CHECKS_REVIEWED, SECURITY_REVIEWED, DISMISSED)
NEEDS_PROVIDER = "add a provider before hiding the first steps"


def first_run_view(practice: Practice) -> dict[str, bool]:
    stored = practice.setup.get(FIRST_RUN_KEY) or {}
    return {step: bool(stored.get(step)) for step in FIRST_RUN_STEPS}


def mark_first_run(practice: Practice, step: str) -> None:
    if step not in FIRST_RUN_STEPS:
        raise ValueError(f"not a first-run step: {step!r}")
    stored = dict(practice.setup.get(FIRST_RUN_KEY) or {})
    if stored.get(step):
        return
    stored[step] = utcnow().isoformat()
    practice.setup = {**practice.setup, FIRST_RUN_KEY: stored}


async def dismiss_first_run(db: AsyncSession, actor: Actor) -> None:
    practice = actor.own_practice
    provider = await db.scalar(
        select(Provider.id).where(Provider.practice_id == practice.id, Provider.active.is_(True)).limit(1)
    )
    if provider is None:
        raise Conflict(NEEDS_PROVIDER)
    mark_first_run(practice, DISMISSED)
    record_activity(db, actor, "first steps hidden", practice_id=practice.id, detail="")
    await db.commit()
