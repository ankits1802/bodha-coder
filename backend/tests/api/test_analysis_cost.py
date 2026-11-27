from __future__ import annotations

import importlib.util
import logging
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from sqlalchemy import select

from app.ai.contracts import ModelReply
from app.core.config import get_settings
from app.core.db import SessionFactory
from app.models import Analysis
from app.worker import process_one
from tests.api.spend_helpers import (
    FLASH,
    FLASH_SNAPSHOT,
    UNLISTED,
    MeteredReviewer,
    Run,
    flash_prices,
    hq_headers,
    record_runs,
    utc,
)
from tests.batches import NoteFile, note_ids_by_file, upload_batch
from tests.builders import FILE_NAME, analysis_deps, practice_with_provider, sign_in, upload_note
from tests.fakes import NOTE_TEXT, text_pdf

MIGRATION = Path(__file__).resolve().parents[2] / "alembic" / "versions" / "0011_analysis_cost.py"
SPEND_LOGGER = "bodha.spend"


def load_migration():
    spec = importlib.util.spec_from_file_location("migration_0011_analysis_cost", MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


async def stored_runs() -> list[tuple]:
    async with SessionFactory() as db:
        rows = await db.execute(
            select(
                Analysis.status,
                Analysis.model,
                Analysis.input_tokens,
                Analysis.output_tokens,
                Analysis.cost_microusd,
                Analysis.price_snapshot,
            ).order_by(Analysis.finished_at)
        )
    return [tuple(row) for row in rows.all()]


async def test_a_read_keeps_what_it_cost_with_top_ups_and_the_prices_used(harness, icd_catalog):
    practice = await practice_with_provider(harness)
    await upload_note(harness, practice)
    reviewer = MeteredReviewer((ModelReply("{}", FLASH, 12_000, 2_500), ModelReply("{}", FLASH, 1_000, 500)))
    assert await process_one(analysis_deps(harness, icd_catalog, reviewer, prices=flash_prices()), get_settings())
    assert await stored_runs() == [("succeeded", FLASH, 13_000, 3_000, 15_500, FLASH_SNAPSHOT)]
    hq = await sign_in(harness.client, "hq-admin@lakeside.example.com", secret_box=practice.secrets)
    overview = (await harness.client.get("/api/hq/overview", headers=hq)).json()
    assert (overview["tokens_last_24h"], overview["cost_last_24h_usd"], overview["unpriced_last_24h"]) == (
        16_000,
        0.02,
        0,
    )


async def test_a_model_without_a_price_records_no_cost_and_is_named_once(harness, icd_catalog, caplog):
    caplog.set_level(logging.WARNING, logger=SPEND_LOGGER)
    practice = await practice_with_provider(harness)
    files = [NoteFile(f"visit {index}.pdf", text_pdf(f"{NOTE_TEXT} {index}"), "99214") for index in (1, 2)]
    await upload_batch(harness, practice, practice.provider_id, date(2026, 11, 25), files)
    deps = analysis_deps(
        harness, icd_catalog, MeteredReviewer((ModelReply("{}", UNLISTED, 4_000, 800),)), prices=flash_prices()
    )
    for _ in files:
        assert await process_one(deps, get_settings())
    assert await stored_runs() == [("succeeded", UNLISTED, 4_000, 800, None, None)] * 2
    warnings = [record.getMessage() for record in caplog.records if record.name == SPEND_LOGGER]
    assert warnings == [f"model {UNLISTED} has no price in MODEL_PRICES; its analyses record no cost"]
    today = datetime.now(UTC).date()
    window = {"from": (today - timedelta(days=1)).isoformat(), "to": (today + timedelta(days=1)).isoformat()}
    report = (await harness.client.get("/api/hq/expenditure", headers=await hq_headers(harness), params=window)).json()
    assert (report["totals"]["unpriced_analyses"], report["totals"]["cost_usd"], report["unpriced_models"]) == (
        2,
        0.0,
        [UNLISTED],
    )


async def test_the_backfill_prices_finished_runs_of_the_default_model_only(harness):
    practice = await practice_with_provider(harness)
    await upload_note(harness, practice)
    note_id = (await note_ids_by_file(harness, practice))[FILE_NAME]
    await record_runs(
        note_id,
        [
            Run("superseded", utc("2026-11-01T09:00:00"), 12_000, 2_500, None),
            Run("superseded", utc("2026-11-02T09:00:00"), 3, 0, None),
            Run("succeeded", utc("2026-11-03T09:00:00"), 1_000, 1_000, None, UNLISTED),
            Run("failed", utc("2026-11-04T09:00:00"), 1_000, 0, None),
            Run("queued", None, 0, 0, None, None),
        ],
    )
    async with SessionFactory() as db:
        await db.execute(load_migration().backfill_statement())
        await db.commit()
    costs = [(status, cost, snapshot) for status, _, _, _, cost, snapshot in await stored_runs()]
    assert costs == [
        ("superseded", 13_500, FLASH_SNAPSHOT),
        ("superseded", 2, FLASH_SNAPSHOT),
        ("succeeded", None, None),
        ("failed", None, None),
        ("queued", None, None),
    ]
