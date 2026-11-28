from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from types import MappingProxyType
from typing import Any

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Actor
from app.core.errors import Invalid
from app.models import UsageEvent, new_id

__all__ = [
    "DECIDING_TASKS",
    "MAX_DURATION_MS",
    "MAX_EVENTS_PER_BATCH",
    "MAX_INPUT_COUNT",
    "STALL_AFTER_MS",
    "TASK_STEPS",
    "UsageRecord",
    "record_usage",
]

MAX_EVENTS_PER_BATCH = 50
MAX_DURATION_MS = 4 * 60 * 60 * 1000
MAX_INPUT_COUNT = 100_000
STALL_AFTER_MS = 60_000
DECIDING_TASKS = frozenset({"note_review"})
TASK_STEPS: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "note_review": ("summary", "note", "findings", "claim", "dialog", "history", "navigation"),
        "queue": ("queue",),
        "upload": ("upload",),
        "billing_export": ("billing",),
    }
)


@dataclass(frozen=True)
class UsageRecord:
    event_id: str
    kind: str
    task: str
    duration_ms: int
    step: str | None = None
    outcome: str | None = None
    first_decision_ms: int | None = None
    key_inputs: int = 0
    pointer_inputs: int = 0
    key_decisions: int = 0
    pointer_decisions: int = 0

    @property
    def decisions(self) -> int:
        return self.key_decisions + self.pointer_decisions


async def record_usage(db: AsyncSession, actor: Actor, records: Sequence[UsageRecord]) -> int:
    unique = {record.event_id: record for record in records}
    for record in unique.values():
        _check(record)
    rows = [_row(actor, record) for record in unique.values()]
    statement = insert(UsageEvent).values(rows).on_conflict_do_nothing(index_elements=["user_id", "client_event_id"])
    result = await db.execute(statement)
    await db.commit()
    return result.rowcount


def _check(record: UsageRecord) -> None:
    if record.kind == "stall":
        _check_stall(record)
    else:
        _check_task(record)


def _check_stall(record: UsageRecord) -> None:
    if record.step not in TASK_STEPS[record.task]:
        raise Invalid(f"the {record.step} step is not part of the {record.task} task")
    if record.duration_ms < STALL_AFTER_MS:
        raise Invalid(f"a stall lasts at least {STALL_AFTER_MS // 1000} seconds")


def _check_task(record: UsageRecord) -> None:
    if record.decisions and record.task not in DECIDING_TASKS:
        raise Invalid(f"the {record.task} task has no findings to decide")
    if (record.first_decision_ms is None) != (record.decisions == 0):
        raise Invalid("time to first decision comes with at least one decision, and only then")
    if record.first_decision_ms is not None and record.first_decision_ms > record.duration_ms:
        raise Invalid("the first decision cannot come after the task ended")


def _row(actor: Actor, record: UsageRecord) -> dict[str, Any]:
    values = asdict(record)
    return {
        **{key: value for key, value in values.items() if key != "event_id"},
        "id": new_id(),
        "client_event_id": record.event_id,
        "practice_id": actor.practice_id,
        "user_id": actor.user.id,
        "role": actor.role,
    }
