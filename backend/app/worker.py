from __future__ import annotations

import asyncio
import logging
import signal
from collections.abc import Awaitable, Callable
from contextlib import suppress
from datetime import UTC, datetime, timedelta

from app.adapters.billing_contract import BillingProvider
from app.adapters.billing_providers import build_billing_providers
from app.adapters.demo_answers import DemoCodeBook
from app.adapters.demo_model import DemoModelClient
from app.adapters.gemini import GeminiClient
from app.adapters.guarded_http import OutboundHttp
from app.adapters.messenger import Messenger, build_messenger
from app.adapters.object_listing import S3ListingStore
from app.adapters.object_store import ObjectStore, S3ObjectStore
from app.adapters.pdf_text import DocumentUnreadable
from app.adapters.sftp import FileLink, ParamikoLink
from app.ai.contracts import ModelClient
from app.ai.errors import ModelRefused, ModelRequestRejected, ModelUnavailable
from app.ai.review import review_note
from app.codes.em import em_ladder
from app.codes.icd import IcdCatalog, IcdReleaseUnavailable, load_catalog
from app.core.config import Settings, get_settings
from app.core.db import SessionFactory
from app.core.error_reports import start_error_reports
from app.core.logging import configure_logging, log_queue_metrics
from app.core.model_prices import PriceBook
from app.models import Analysis, utcnow
from app.services.ack_polling import poll_acknowledgments
from app.services.analysis import AnalysisDeps, claim_next, fail_attempt, run_analysis, stale_running
from app.services.digests import send_due_digests
from app.services.ehr_pull import poll_ehr_connections
from app.services.email_intake import poll_email_intake
from app.services.evaluation_runs import fail_evaluation, fail_stale_evaluations, next_queued_evaluation, run_evaluation
from app.services.file_sweep import sweep_orphan_files
from app.services.intake import poll_intake
from app.services.job_control import queue_counts, requeue_interrupted
from app.services.plan_notices import notify_plans_ending
from app.services.quantity_sync import sync_quantities
from app.services.query_governance import escalate_unanswered
from app.services.reminders import expire_requests, send_due_reminders
from app.services.retention import purge_access_logs

logger = logging.getLogger("bodha.worker")
RETRY_DELAYS = (timedelta(seconds=30), timedelta(minutes=2), timedelta(minutes=10))
RECOVERY_INTERVAL_SECONDS = 60
REMINDER_INTERVAL_SECONDS = 300
METRICS_INTERVAL_SECONDS = 60
PURGE_INTERVAL_SECONDS = 86_400
INTAKE_INTERVAL_SECONDS = 60
EHR_INTERVAL_SECONDS = 60
EVALUATION_INTERVAL_SECONDS = 60
ESCALATION_INTERVAL_SECONDS = 3_600
SWEEP_INTERVAL_SECONDS = 86_400
QUANTITY_SYNC_INTERVAL_SECONDS = 900
PLAN_NOTICE_INTERVAL_SECONDS = 3_600
ACKNOWLEDGMENT_INTERVAL_SECONDS = 600
STALE_EVALUATION = timedelta(hours=6)
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


async def every(seconds: float, name: str, job: Callable[[], Awaitable[object]]) -> None:
    while True:
        try:
            await job()
        except Exception:
            logger.exception("%s failed", name)
        await asyncio.sleep(seconds)


async def poll_intake_once(store: S3ListingStore) -> None:
    async with SessionFactory() as db:
        await poll_intake(db, store, utcnow())


async def poll_email_intake_once(store: S3ListingStore, inbound: S3ListingStore) -> None:
    async with SessionFactory() as db:
        await poll_email_intake(db, store, utcnow(), inbound=inbound)


async def poll_ehr_once(store: S3ListingStore, outbound: OutboundHttp) -> None:
    async with SessionFactory() as db:
        await poll_ehr_connections(db, store, outbound, utcnow())


async def sweep_files_once(store: S3ListingStore) -> None:
    async with SessionFactory() as db:
        await sweep_orphan_files(db, store, utcnow())


async def poll_acknowledgments_once(store: ObjectStore, link: FileLink) -> None:
    async with SessionFactory() as db:
        await poll_acknowledgments(db, store, link, utcnow())


async def escalate_once(messenger: Messenger) -> None:
    async with SessionFactory() as db:
        await escalate_unanswered(db, messenger, utcnow())


async def notify_plans_ending_once() -> None:
    async with SessionFactory() as db:
        await notify_plans_ending(db, utcnow())


async def sync_quantities_once(billing: dict[str, BillingProvider]) -> None:
    async with SessionFactory() as db:
        await sync_quantities(db, billing)


async def evaluate_once(deps: AnalysisDeps) -> None:
    async with SessionFactory() as db:
        await fail_stale_evaluations(db, older_than=STALE_EVALUATION)
        run_id = await next_queued_evaluation(db)
        if run_id is None:
            return
        try:
            await run_evaluation(db, run_id, deps)
        except Exception as error:
            await db.rollback()
            await fail_evaluation(db, run_id, failure_reason(error))
            raise


def model_client(settings: Settings, icd: IcdCatalog) -> ModelClient:
    if settings.gemini_backend == "demo":
        return DemoModelClient(DemoCodeBook(em_ladder=em_ladder, icd_name=icd.describe))
    return GeminiClient(settings)


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
    start_error_reports(settings, process="worker")
    icd = await asyncio.to_thread(load_catalog)
    deps = AnalysisDeps(
        review_note, model_client(settings, icd), S3ObjectStore(settings), icd, PriceBook(settings.model_prices)
    )
    loops = [worker_loop(deps, settings) for _ in range(settings.ai_workers)]
    messenger, listing = build_messenger(settings), S3ListingStore(settings)
    inbound = S3ListingStore(settings, bucket=settings.email_intake_bucket) if settings.email_intake_bucket else listing
    billing = build_billing_providers(settings)
    link = ParamikoLink(timeout_seconds=settings.clearinghouse_timeout_seconds)
    everything = asyncio.gather(
        *loops,
        recovery_loop(settings),
        reminder_loop(messenger),
        metrics_loop(),
        purge_loop(),
        every(INTAKE_INTERVAL_SECONDS, "intake", lambda: poll_intake_once(listing)),
        every(INTAKE_INTERVAL_SECONDS, "email intake", lambda: poll_email_intake_once(listing, inbound)),
        every(EHR_INTERVAL_SECONDS, "EHR pull", lambda: poll_ehr_once(listing, OutboundHttp())),
        every(EVALUATION_INTERVAL_SECONDS, "evaluation", lambda: evaluate_once(deps)),
        every(ESCALATION_INTERVAL_SECONDS, "escalation", lambda: escalate_once(messenger)),
        every(SWEEP_INTERVAL_SECONDS, "orphan file sweep", lambda: sweep_files_once(listing)),
        every(QUANTITY_SYNC_INTERVAL_SECONDS, "subscription quantity sync", lambda: sync_quantities_once(billing)),
        every(PLAN_NOTICE_INTERVAL_SECONDS, "plan ending notices", notify_plans_ending_once),
        every(
            ACKNOWLEDGMENT_INTERVAL_SECONDS,
            "clearinghouse responses",
            lambda: poll_acknowledgments_once(deps.store, link),
        ),
    )
    with suppress(NotImplementedError):
        asyncio.get_running_loop().add_signal_handler(signal.SIGTERM, everything.cancel)
    with suppress(asyncio.CancelledError):
        await everything


if __name__ == "__main__":
    configure_logging()
    asyncio.run(run())
