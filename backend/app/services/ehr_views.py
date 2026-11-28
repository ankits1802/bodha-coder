from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Actor
from app.models import PULL_OUTCOMES, EhrDocument, EhrKey, EhrPullRun, utcnow
from app.services.ehr_keys import current_key, ehr_ready, jwks_url, key_id_of
from app.services.ehr_settings import DEFAULT_SCOPES, connection_json, latest_connection

__all__ = [
    "AUTH_METHOD",
    "CONNECTION_STATUSES",
    "DOCUMENT_PAGE",
    "GRANT_TYPE",
    "INTERRUPTED_AFTER",
    "RUN_PAGE",
    "RUN_STATES",
    "connection_view",
    "document_page",
    "run_page",
    "run_view",
]

GRANT_TYPE = "client_credentials"
AUTH_METHOD = "private_key_jwt"
RUN_PAGE = 20
DOCUMENT_PAGE = 50
INTERRUPTED_AFTER = timedelta(minutes=30)
CONNECTION_STATUSES = ("unavailable", "off", "incomplete", "paused", "pulling")
RUN_STATES = (*PULL_OUTCOMES, "running", "interrupted")


async def connection_view(db: AsyncSession, actor: Actor) -> dict[str, Any]:
    key = await current_key(db, actor.practice_id)
    connection = await latest_connection(db, actor.practice_id)
    last = await db.scalar(
        select(EhrPullRun)
        .where(EhrPullRun.practice_id == actor.practice_id)
        .order_by(EhrPullRun.created_at.desc(), EhrPullRun.id)
        .limit(1)
    )
    available = ehr_ready()
    return {
        "available": available,
        "status": _status(available, key is not None, connection.paused if connection else None),
        "registration": _registration(key) if key else None,
        "connection": connection_json(connection) if connection else None,
        "default_scopes": list(DEFAULT_SCOPES),
        "last_run": run_view(last, utcnow()) if last else None,
    }


async def run_page(db: AsyncSession, actor: Actor, *, offset: int) -> dict[str, Any]:
    mine = EhrPullRun.practice_id == actor.practice_id
    rows = (
        await db.scalars(
            select(EhrPullRun)
            .where(mine)
            .order_by(EhrPullRun.created_at.desc(), EhrPullRun.id)
            .offset(offset)
            .limit(RUN_PAGE)
        )
    ).all()
    total = await db.scalar(select(func.count()).select_from(EhrPullRun).where(mine)) or 0
    now = utcnow()
    return {"items": [run_view(row, now) for row in rows], "total": total, "offset": offset, "page_size": RUN_PAGE}


async def document_page(db: AsyncSession, actor: Actor, *, offset: int) -> dict[str, Any]:
    mine = EhrDocument.practice_id == actor.practice_id
    rows = (
        await db.scalars(
            select(EhrDocument)
            .where(mine)
            .order_by(EhrDocument.created_at.desc(), EhrDocument.id)
            .offset(offset)
            .limit(DOCUMENT_PAGE)
        )
    ).all()
    total = await db.scalar(select(func.count()).select_from(EhrDocument).where(mine)) or 0
    return {
        "items": [_document_view(row) for row in rows],
        "total": total,
        "offset": offset,
        "page_size": DOCUMENT_PAGE,
    }


def run_view(run: EhrPullRun, now: datetime) -> dict[str, Any]:
    return {
        "id": run.id,
        "started_at": run.created_at.isoformat(),
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "outcome": run.outcome or ("running" if now - run.created_at < INTERRUPTED_AFTER else "interrupted"),
        "reason": run.reason,
        "pages": run.pages or 0,
        "accepted": run.accepted or 0,
        "duplicates": run.duplicates or 0,
        "refused": run.refused or 0,
        "skipped": run.skipped or 0,
    }


def _document_view(row: EhrDocument) -> dict[str, Any]:
    return {
        "id": row.id,
        "fetched_at": row.created_at.isoformat(),
        "document_id": row.document_id,
        "outcome": row.outcome,
        "reason": row.reason,
        "note_id": row.note_id,
    }


def _registration(key: EhrKey) -> dict[str, Any]:
    return {
        "jwks_url": jwks_url(key.key_set),
        "key_id": key_id_of(key),
        "algorithm": key.algorithm,
        "key_created_at": key.created_at.isoformat(),
        "grant_type": GRANT_TYPE,
        "auth_method": AUTH_METHOD,
    }


def _status(available: bool, has_key: bool, paused: bool | None) -> str:
    if not available:
        return "unavailable"
    if paused is None:
        return "off"
    if not has_key:
        return "incomplete"
    return "paused" if paused else "pulling"
