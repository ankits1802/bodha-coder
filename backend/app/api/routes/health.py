from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable
from typing import Any, Protocol

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.deps import Db

router = APIRouter(tags=["health"])
logger = logging.getLogger("bodha.health")
READY_TIMEOUT_SECONDS = 2.0
PASSED = "ok"
FAILED = "unavailable"


class BucketCheck(Protocol):
    async def check_bucket(self) -> None: ...


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
async def ready(request: Request, db: Db) -> JSONResponse:
    store: BucketCheck = request.app.state.store
    database, storage = await asyncio.gather(
        _outcome("database", db.execute(text("SELECT 1"))), _outcome("storage", store.check_bucket())
    )
    checks = {"database": database, "storage": storage}
    is_ready = all(result == PASSED for result in checks.values())
    body = {"status": "ready" if is_ready else "not ready", "checks": checks}
    return JSONResponse(body, status_code=200 if is_ready else 503)


async def _outcome(name: str, check: Awaitable[Any]) -> str:
    try:
        await asyncio.wait_for(check, timeout=READY_TIMEOUT_SECONDS)
    except Exception as error:
        logger.warning("readiness check failed", extra={"fields": {"check": name, "error": type(error).__name__}})
        return FAILED
    return PASSED
