from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from app.adapters.gemini import GeminiClient
from app.adapters.object_store import S3ObjectStore
from app.adapters.pdf_text import DocumentUnreadable
from app.ai.errors import ModelRefused, ModelRequestRejected, ModelUnavailable
from app.ai.review import review_note
from app.codes.icd import IcdReleaseUnavailable, load_catalog
from app.core.config import Settings, get_settings
from app.core.db import SessionFactory
from app.models import Analysis
from app.services.analysis import AnalysisDeps, claim_next, fail_attempt, run_analysis, stale_running

logger = logging.getLogger("bodha.worker")
RETRY_DELAYS = (timedelta(seconds=30), timedelta(minutes=2), timedelta(minutes=10))
RECOVERY_INTERVAL_SECONDS = 60
PERMANENT_FAILURES = (DocumentUnreadable, ModelRefused, ModelRequestRejected, IcdReleaseUnavailable)


def failure_reason(error: Exception) -> str:
    if isinstance(error, TimeoutError):
        return "Reading this note took too long."
    if isinstance(error, PERMANENT_FAILURES + (ModelUnavailable,)) and str(error):
        return str(error)
    if isinstance(error, OSError):
        return "A storage or network error stopped the read."
    return f"Something went wrong while reading this note ({type(error).__name__})."


def retry_delay(attempts: int, settings: Settings) -> timedelta | None:
    if attempts >= settings.ai_max_attempts:
        return None
    return RETRY_DELAYS[min(attempts, len(RETRY_DELAYS)) - 1]


async def process_one(deps: AnalysisDeps, settings: Settings) -> bool:
    async with SessionFactory() as db:
        claimed = await claim_next(db)
        if claimed is None:
            return False
        analysis_id, attempts = claimed.id, claimed.attempts
        try:
            await asyncio.wait_for(run_analysis(db, claimed, deps), timeout=settings.ai_job_timeout_seconds)
            return True
        except PERMANENT_FAILURES as error:
            reason, retry_in = failure_reason(error), None
        except (ModelUnavailable, TimeoutError, OSError) as error:
            reason, retry_in = failure_reason(error), retry_delay(attempts, settings)
        except Exception as error:
            logger.exception("analysis %s failed unexpectedly", analysis_id)
            reason, retry_in = failure_reason(error), None
        await db.rollback()
        await fail_attempt(db, await db.get_one(Analysis, analysis_id), reason, retry_in=retry_in)
        return True


async def worker_loop(deps: AnalysisDeps, settings: Settings) -> None:
    while True:
        if not await process_one(deps, settings):
            await asyncio.sleep(settings.ai_poll_seconds)


async def recovery_loop(settings: Settings) -> None:
    older_than = timedelta(seconds=settings.ai_job_timeout_seconds * 2)
    while True:
        async with SessionFactory() as db:
            for analysis in await stale_running(db, older_than=older_than):
                await fail_attempt(
                    db, analysis, "worker stopped while running", retry_in=retry_delay(analysis.attempts, settings)
                )
        await asyncio.sleep(RECOVERY_INTERVAL_SECONDS)


async def run() -> None:
    settings = get_settings()
    deps = AnalysisDeps(
        review_note, GeminiClient(settings), S3ObjectStore(settings), await asyncio.to_thread(load_catalog)
    )
    loops = [worker_loop(deps, settings) for _ in range(settings.ai_workers)]
    await asyncio.gather(*loops, recovery_loop(settings))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())
