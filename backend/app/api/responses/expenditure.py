from typing import Literal

from pydantic import Field

from app.api.responses.base import View
from app.services.expenditure import SPEND_TIME_ZONE
from app.services.plans import PLAN_KEYS

__all__ = ["Expenditure", "PracticeSpend", "ProviderSpend", "SpendFigures"]


class SpendFigures(View):
    analyses: int
    notes: int
    input_tokens: int
    output_tokens: int
    cost_usd: float
    cost_per_note_usd: float | None
    unpriced_analyses: int


class ProviderSpend(SpendFigures):
    id: str
    name: str


class PracticeSpend(SpendFigures):
    id: str
    name: str
    plan: Literal[PLAN_KEYS]
    plan_monthly_cents: int | None
    providers: list[ProviderSpend]


class Expenditure(View):
    start: str = Field(alias="from")
    end: str = Field(alias="to")
    time_zone: Literal[SPEND_TIME_ZONE]
    totals: SpendFigures
    practices: list[PracticeSpend]
    unpriced_models: list[str]
