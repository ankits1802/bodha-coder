from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from statistics import median
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import QUESTIONS_PURPOSE, AddendumRequest, Note, Provider
from app.services.addenda import DEFAULT_OPTIONS, OTHER_ANSWER
from app.services.query_governance import ASKED_STATUSES

__all__ = ["NOT_AGREED", "AskedRequest", "QueryMetrics", "metrics_for", "query_metrics", "repeated_keys"]

NOT_AGREED = frozenset((*DEFAULT_OPTIONS[1:], OTHER_ANSWER))
RATE_DIGITS = 4
TENTHS = 1


@dataclass(frozen=True)
class AskedRequest:
    provider_id: str
    note_id: str
    sent_at: datetime
    answered_at: datetime | None
    keys: tuple[str, ...]
    choices: tuple[str, ...]
    repeated: int


@dataclass(frozen=True)
class QueryMetrics:
    notes: int
    queries: int
    per_100_notes: float | None
    response_rate: float | None
    median_hours: float | None
    agree_rate: float | None
    repeat_rate: float | None


def metrics_for(notes: int, requests: Sequence[AskedRequest]) -> QueryMetrics:
    queries = sum(len(item.keys) for item in requests)
    answered = [item for item in requests if item.answered_at is not None]
    choices = [choice for item in answered for choice in item.choices]
    hours = [(item.answered_at - item.sent_at).total_seconds() / 3600 for item in answered if item.answered_at]
    return QueryMetrics(
        notes=notes,
        queries=queries,
        per_100_notes=round(queries * 100 / notes, TENTHS) if notes else None,
        response_rate=_share(sum(len(item.keys) for item in answered), queries),
        median_hours=round(median(hours), TENTHS) if hours else None,
        agree_rate=_share(sum(choice not in NOT_AGREED for choice in choices), len(choices)),
        repeat_rate=_share(sum(item.repeated for item in requests), queries),
    )


def _share(part: int, whole: int) -> float | None:
    return round(part / whole, RATE_DIGITS) if whole else None


def repeated_keys(keys: Iterable[str], asked_before: set[str]) -> int:
    return sum(1 for key in keys if key in asked_before)


async def query_metrics(db: AsyncSession, practice_id: str, *, days: int, now: datetime) -> dict[str, Any]:
    since = now - timedelta(days=days)
    notes = await _notes_by_provider(db, practice_id, since)
    asked = await _asked_requests(db, practice_id, since)
    names = await _provider_names(db, set(notes) | {item.provider_id for item in asked})
    providers = [
        {
            "provider_id": provider_id,
            "provider_name": names.get(provider_id, ""),
            **asdict(
                metrics_for(notes.get(provider_id, 0), [item for item in asked if item.provider_id == provider_id])
            ),
        }
        for provider_id in sorted(names, key=lambda key: (names[key].lower(), key))
    ]
    return {"days": days, "total": asdict(metrics_for(sum(notes.values()), asked)), "providers": providers}


async def _notes_by_provider(db: AsyncSession, practice_id: str, since: datetime) -> dict[str, int]:
    rows = await db.execute(
        select(Note.provider_id, func.count())
        .where(Note.practice_id == practice_id, Note.created_at >= since)
        .group_by(Note.provider_id)
    )
    return {provider_id: count for provider_id, count in rows.all()}


async def _asked_requests(db: AsyncSession, practice_id: str, since: datetime) -> list[AskedRequest]:
    recent = (
        await db.scalars(
            select(AddendumRequest).where(
                AddendumRequest.practice_id == practice_id,
                AddendumRequest.created_at >= since,
                AddendumRequest.status.in_(ASKED_STATUSES),
                AddendumRequest.purpose == QUESTIONS_PURPOSE,
            )
        )
    ).all()
    history = await _asked_history(db, {item.note_id for item in recent})
    return [_asked(item, history.get(item.note_id, [])) for item in recent]


async def _asked_history(db: AsyncSession, note_ids: set[str]) -> dict[str, list[tuple[datetime, set[str]]]]:
    if not note_ids:
        return {}
    rows = await db.execute(
        select(AddendumRequest.note_id, AddendumRequest.created_at, AddendumRequest.questions).where(
            AddendumRequest.note_id.in_(note_ids),
            AddendumRequest.status.in_(ASKED_STATUSES),
            AddendumRequest.purpose == QUESTIONS_PURPOSE,
        )
    )
    found: dict[str, list[tuple[datetime, set[str]]]] = {}
    for note_id, sent_at, questions in rows.all():
        found.setdefault(note_id, []).append((sent_at, {str(item["key"]) for item in questions}))
    return found


def _asked(request: AddendumRequest, history: list[tuple[datetime, set[str]]]) -> AskedRequest:
    before = set().union(*(keys for sent_at, keys in history if sent_at < request.created_at))
    keys = tuple(str(item["key"]) for item in request.questions)
    choices = tuple(str(item["choice"]) for item in request.answers or ()) if request.status == "answered" else ()
    return AskedRequest(
        provider_id=request.provider_id,
        note_id=request.note_id,
        sent_at=request.created_at,
        answered_at=request.answered_at if request.status == "answered" else None,
        keys=keys,
        choices=choices,
        repeated=repeated_keys(keys, before),
    )


async def _provider_names(db: AsyncSession, provider_ids: set[str]) -> Mapping[str, str]:
    if not provider_ids:
        return {}
    rows = await db.execute(select(Provider.id, Provider.name).where(Provider.id.in_(provider_ids)))
    return {provider_id: name for provider_id, name in rows.all()}
