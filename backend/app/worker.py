from __future__ import annotations

import asyncio
import logging
import signal
from contextlib import suppress
from datetime import UTC, datetime, timedelta

from app.adapters.gemini import GeminiClient
from app.adapters.messenger import Messenger, build_messenger
from app.adapters.object_store import S3ObjectStore
from app.adapters.pdf_text import DocumentUnreadable
from app.ai.errors import ModelRefused, ModelRequestRejected, ModelUnavailable
from app.ai.review import review_note
from app.codes.icd import IcdReleaseUnavailable, load_catalog
from app.core.config import Settings, get_settings
from app.core.db import SessionFactory
from app.core.logging import configure_logging, log_queue_metrics
from app.models import Analysis, utcnow
from app.services.analysis import AnalysisDeps, claim_next, fail_attempt, run_analysis, stale_running
from app.services.digests import send_due_digests
from app.services.job_control import queue_counts, requeue_interrupted
from app.services.records import purge_access_logs
from app.services.reminders import expire_requests, send_due_reminders

logger = logging.getLogger("bodha.worker")
RETRY_DELAYS = (timedelta(seconds=30), timedelta(minutes=2), timedelta(minutes=10))
RECOVERY_INTERVAL_SECONDS = 60
REMINDER_INTERVAL_SECONDS = 300
METRICS_INTERVAL_SECONDS = 60
PURGE_INTERVAL_SECONDS = 86_400
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
        except asyncio.CancelledError:
            await asyncio.shield(_hand_back(analysis_id))
            raise
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


async def _hand_back(analysis_id: str) -> None:
    async with SessionFactory() as db:
        await requeue_interrupted(db, analysis_id)
    logger.info("analysis %s handed back to the queue on shutdown", analysis_id)


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


async def reminder_loop(messenger: Messenger) -> None:
    while True:
        try:
            async with SessionFactory() as db:
                await expire_requests(db)
                await send_due_reminders(db, messenger)
                await send_due_digests(db, messenger, utcnow())
        except Exception:
            logger.exception("provider reminders failed")
        await asyncio.sleep(REMINDER_INTERVAL_SECONDS)


async def metrics_loop() -> None:
    while True:
        try:
            async with SessionFactory() as db:
                queued, running = await queue_counts(db)
            log_queue_metrics(logger, queued=queued, running=running, at=datetime.now(UTC))
        except Exception:
            logger.exception("queue metrics failed")
        await asyncio.sleep(METRICS_INTERVAL_SECONDS)


async def purge_loop() -> None:
    while True:
        try:
            async with SessionFactory() as db:
                await purge_access_logs(db, utcnow())
        except Exception:
            logger.exception("access log purge failed")
        await asyncio.sleep(PURGE_INTERVAL_SECONDS)


async def run() -> None:
    settings = get_settings()
    deps = AnalysisDeps(
        review_note, GeminiClient(settings), S3ObjectStore(settings), await asyncio.to_thread(load_catalog)
    )
    loops = [worker_loop(deps, settings) for _ in range(settings.ai_workers)]
    everything = asyncio.gather(
        *loops, recovery_loop(settings), reminder_loop(build_messenger(settings)), metrics_loop(), purge_loop()
    )
    with suppress(NotImplementedError):
        asyncio.get_running_loop().add_signal_handler(signal.SIGTERM, everything.cancel)
    with suppress(asyncio.CancelledError):
        await everything


if __name__ == "__main__":
    configure_logging()
    asyncio.run(run())
