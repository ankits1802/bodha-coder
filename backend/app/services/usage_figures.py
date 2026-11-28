from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import ColumnElement, Float, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import UsageEvent, utcnow

__all__ = ["QUARTILES", "hq_usage", "practice_usage"]

QUARTILES = (0.25, 0.5, 0.75)
SECOND_DECIMALS = 1
SHARE_DECIMALS = 3
MS_PER_SECOND = 1000.0


async def practice_usage(db: AsyncSession, practice_id: str, *, days: int) -> dict[str, Any]:
    where = (UsageEvent.practice_id == practice_id, UsageEvent.created_at >= _since(days))
    return {"days": days, "tasks": await _task_rows(db, where), "stalls": await _stall_rows(db, where)}


async def hq_usage(db: AsyncSession, *, days: int) -> dict[str, Any]:
    where = (UsageEvent.created_at >= _since(days),)
    practices = await db.scalar(select(func.count(func.distinct(UsageEvent.practice_id))).where(*where))
    return {
        "days": days,
        "practices": practices or 0,
        "tasks": await _task_rows(db, where),
        "stalls": await _stall_rows(db, where),
    }


def _since(days: int) -> datetime:
    return utcnow() - timedelta(days=days)


def _quartiles(column: ColumnElement[Any]) -> list[ColumnElement[Any]]:
    return [func.percentile_cont(share).within_group(column) for share in QUARTILES]


def _inputs_per_decision() -> ColumnElement[Any]:
    inputs = cast(UsageEvent.key_inputs + UsageEvent.pointer_inputs, Float)
    return inputs / func.nullif(UsageEvent.key_decisions + UsageEvent.pointer_decisions, 0)


async def _task_rows(db: AsyncSession, where: Sequence[ColumnElement[bool]]) -> list[dict[str, Any]]:
    query = (
        select(
            UsageEvent.task,
            UsageEvent.role,
            func.count(),
            func.count().filter(UsageEvent.outcome == "completed"),
            func.count(func.distinct(UsageEvent.user_id)),
            func.coalesce(func.sum(UsageEvent.key_decisions), 0),
            func.coalesce(func.sum(UsageEvent.pointer_decisions), 0),
            *_quartiles(UsageEvent.duration_ms),
            *_quartiles(UsageEvent.first_decision_ms),
            *_quartiles(_inputs_per_decision()),
        )
        .where(UsageEvent.kind == "task", *where)
        .group_by(UsageEvent.task, UsageEvent.role)
        .order_by(UsageEvent.task, UsageEvent.role)
    )
    return [_task_row(row) for row in (await db.execute(query)).all()]


def _task_row(row: Sequence[Any]) -> dict[str, Any]:
    task, role, tasks, completed, people, by_key, by_pointer = row[:7]
    decided = by_key + by_pointer
    return {
        "task": task,
        "role": role,
        "tasks": tasks,
        "completed": completed,
        "people": people,
        "duration": _seconds(row[7:10]),
        "first_decision": _seconds(row[10:13]),
        "decided": decided,
        "inputs_per_decision": _spread(row[13:16], scale=1.0),
        "keyboard_share": round(by_key / decided, SHARE_DECIMALS) if decided else None,
    }


async def _stall_rows(db: AsyncSession, where: Sequence[ColumnElement[bool]]) -> list[dict[str, Any]]:
    query = (
        select(
            UsageEvent.task,
            UsageEvent.step,
            UsageEvent.role,
            func.count(),
            func.count(func.distinct(UsageEvent.user_id)),
            *_quartiles(UsageEvent.duration_ms),
        )
        .where(UsageEvent.kind == "stall", *where)
        .group_by(UsageEvent.task, UsageEvent.step, UsageEvent.role)
        .order_by(UsageEvent.task, UsageEvent.step, UsageEvent.role)
    )
    rows = (await db.execute(query)).all()
    return [
        {"task": task, "step": step, "role": role, "stalls": stalls, "people": people, "duration": _seconds(rest)}
        for task, step, role, stalls, people, *rest in rows
    ]


def _seconds(values: Sequence[float | None]) -> dict[str, float] | None:
    return _spread(values, scale=MS_PER_SECOND)


def _spread(values: Sequence[float | None], *, scale: float) -> dict[str, float] | None:
    if any(value is None for value in values):
        return None
    low, middle, high = (round(value / scale, SECOND_DECIMALS) for value in values)
    return {"p25": low, "median": middle, "p75": high}
