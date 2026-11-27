from typing import Literal

from app.api.responses.base import Omittable, View
from app.api.responses.notes import CodeJson
from app.api.responses.quality import ClaimElements, ElementComparison, Rate

__all__ = [
    "EvalCandidate",
    "EvalCandidateList",
    "EvalCaseAdded",
    "EvalCaseList",
    "EvalCaseResult",
    "EvalCaseRow",
    "EvalConsistency",
    "EvalDeltas",
    "EvalRunChange",
    "EvalRunDetail",
    "EvalRunView",
    "EvalRuns",
    "EvalSummary",
    "ExpectedClaim",
]

EvalMetric = Literal["em", "icd_f1", "modifiers"]


class EvalConsistency(View):
    em: Rate
    icd: Rate
    modifiers: Rate
    all: Rate


class EvalSummary(View):
    cases: Omittable[int] = None
    scored: Omittable[int] = None
    failed: Omittable[int] = None
    em: Omittable[Rate] = None
    em_higher: Omittable[Rate] = None
    em_lower: Omittable[Rate] = None
    icd_precision: Omittable[Rate] = None
    icd_recall: Omittable[Rate] = None
    icd_f1: Omittable[float | None] = None
    modifiers: Omittable[Rate] = None
    consistency: Omittable[EvalConsistency] = None
    error: Omittable[str] = None


class EvalDeltas(View):
    em: Omittable[float] = None
    icd_f1: Omittable[float] = None
    modifiers: Omittable[float] = None


class EvalRunChange(View):
    deltas: EvalDeltas
    dropped: list[EvalMetric]
    status: Literal["dropped", "holding"]


class EvalRunView(View):
    id: str
    status: Literal["queued", "running", "done", "failed"]
    model: str
    prompt_version: str
    requested_at: str | None
    finished_at: str | None
    summary: EvalSummary
    change: EvalRunChange | None


class EvalRuns(View):
    cases: int
    runs: list[EvalRunView]


class ExpectedClaim(View):
    em: str | None
    icd: list[str]
    modifiers: list[str]
    level: str | None
    claim: list[CodeJson]
    analysis_id: str


class EvalCaseResult(View):
    case_id: str
    note_id: str
    expected: ExpectedClaim
    error: Omittable[str] = None
    model: Omittable[str | None] = None
    prompt_version: Omittable[str] = None
    input_tokens: Omittable[int] = None
    output_tokens: Omittable[int] = None
    runs: Omittable[list[ClaimElements]] = None
    agreement: Omittable[ElementComparison] = None
    repeat: Omittable[ElementComparison] = None
    service_date: Omittable[str] = None
    provider_name: Omittable[str] = None


class EvalRunDetail(View):
    run: EvalRunView
    results: list[EvalCaseResult]


class EvalCaseRow(View):
    note_id: str
    provider_name: str
    service_date: str
    em: str | None
    level: str | None
    icd: list[str]
    modifiers: list[str]
    added_at: str


class EvalCaseList(View):
    items: list[EvalCaseRow]


class EvalCandidate(View):
    note_id: str
    provider_name: str
    service_date: str
    codes: list[str]


class EvalCandidateList(View):
    items: list[EvalCandidate]


class EvalCaseAdded(View):
    id: str
    note_id: str
