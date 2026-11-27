from typing import Literal

from app.api.responses.base import View

__all__ = [
    "DayCount",
    "EmBenchmark",
    "EmMix",
    "EmMixFamily",
    "EmMixLevel",
    "EmMixProvider",
    "InsightEstimates",
    "Insights",
    "Outcomes",
    "PersonProductivity",
    "ProviderEstimate",
    "ProviderOutcome",
    "ProviderQueryMetrics",
    "QueryMetrics",
    "QueryMetricsReport",
]


class DayCount(View):
    date: str
    notes: int


class Outcomes(View):
    matched: int
    billed_too_low: int
    billed_too_high: int
    diagnosis_changes: int


class ProviderOutcome(View):
    provider_name: str
    notes: int
    matched: int


class ProviderEstimate(View):
    provider_name: str
    notes: int
    difference: float


class InsightEstimates(View):
    notes: int
    difference: float
    providers: list[ProviderEstimate]


class PersonProductivity(View):
    id: str
    name: str
    approved: int
    median_minutes: float | None
    changed: int


class Insights(View):
    days: int
    per_day: list[DayCount]
    approved: int
    approved_on_time: int
    outcomes: Outcomes
    providers: list[ProviderOutcome]
    estimates: InsightEstimates
    people: list[PersonProductivity]


class EmMixLevel(View):
    code: str
    count: int
    share: float
    benchmark: float | None
    points: float | None
    direction: Literal["above", "below"] | None


class EmMixFamily(View):
    family: str
    label: str
    visits: int
    has_benchmark: bool
    levels: list[EmMixLevel]
    chi_square: float | None
    degrees_of_freedom: int | None
    p_value: float | None
    outlier: bool
    reasons: list[Literal["points", "chi_square"]]
    lean: Literal["higher", "lower"] | None


class EmMixProvider(View):
    id: str
    name: str
    specialty: str | None
    cms_specialty: str | None
    visits: int
    families: list[EmMixFamily]


class EmBenchmark(View):
    dataset: str
    year: str
    source_url: str


class EmMix(View):
    start: str
    end: str
    benchmark: EmBenchmark
    providers: list[EmMixProvider]


class QueryMetrics(View):
    notes: int
    queries: int
    per_100_notes: float | None
    response_rate: float | None
    median_hours: float | None
    agree_rate: float | None
    repeat_rate: float | None


class ProviderQueryMetrics(QueryMetrics):
    provider_id: str
    provider_name: str


class QueryMetricsReport(View):
    days: int
    total: QueryMetrics
    providers: list[ProviderQueryMetrics]
