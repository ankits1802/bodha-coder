from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select

from app.ai.contracts import ModelClient, ModelReply, ReviewInputs, ReviewOutcome
from app.core.db import SessionFactory
from app.core.model_prices import ModelPrice, PriceBook
from app.models import Analysis
from tests.builders import Harness, create_hq_user, marisol_report, sign_in

FLASH = "gemini-3.8-flash"
UNLISTED = "gemini-unlisted"
FLASH_SNAPSHOT = {FLASH: {"input": 0.5, "output": 3.0}}
HQ_EMAIL = "owner@bodha.example.com"
FIGURES = ("analyses", "notes", "input_tokens", "output_tokens", "cost_usd", "cost_per_note_usd", "unpriced_analyses")


def flash_prices() -> PriceBook:
    return PriceBook({FLASH: ModelPrice(input=Decimal("0.50"), output=Decimal("3.00"))})


@dataclass
class MeteredReviewer:
    replies: tuple[ModelReply, ...]

    async def __call__(self, client: ModelClient, inputs: ReviewInputs) -> ReviewOutcome:
        return ReviewOutcome(report=marisol_report(), prompt_version="test", replies=self.replies)


@dataclass(frozen=True)
class Run:
    status: str
    finished: datetime | None
    input_tokens: int
    output_tokens: int
    cost_microusd: int | None
    model: str | None = FLASH


def utc(text: str) -> datetime:
    return datetime.fromisoformat(text).replace(tzinfo=UTC)


async def record_runs(note_id: str, runs: list[Run]) -> None:
    async with SessionFactory() as db:
        first = await db.scalar(select(Analysis).where(Analysis.note_id == note_id, Analysis.revision == 1))
        assert first is not None
        for revision, run in enumerate(runs, start=1):
            row = first if revision == 1 else Analysis(note_id=note_id, revision=revision, reason="rerun", context={})
            row.status, row.model, row.finished_at = run.status, run.model, run.finished
            row.input_tokens, row.output_tokens = run.input_tokens, run.output_tokens
            row.cost_microusd = run.cost_microusd
            db.add(row)
        await db.commit()


async def hq_headers(harness: Harness) -> dict[str, str]:
    await create_hq_user(HQ_EMAIL)
    return await sign_in(harness.client, HQ_EMAIL)


def figures(*values: int | float | None) -> dict[str, int | float | None]:
    return dict(zip(FIGURES, values, strict=True))


def figures_of(row: dict) -> dict[str, int | float | None]:
    return {name: row[name] for name in FIGURES}
