from typing import Literal

from app.api.responses.base import Lane, NoteStatus, View
from app.models.tables import LANE_REASONS
from app.services.queue_views import BUILTIN_KEYS
from app.services.worklists import QUEUE_SORTS

__all__ = [
    "BatchProgress",
    "ComplianceList",
    "CompliancePattern",
    "ComplianceRow",
    "EmAction",
    "LaneCount",
    "LaneCounts",
    "LaneReason",
    "BuiltinView",
    "NoteSummary",
    "ProviderReasonCounts",
    "QueuePage",
    "QueueRow",
    "QueueSort",
    "QueueViewFilters",
    "QueueViews",
    "SavedView",
    "SearchResults",
    "TodaySummary",
]

LaneReason = Literal[LANE_REASONS]
QueueSort = Literal[QUEUE_SORTS]
EmAction = Literal["keep", "lower", "raise", "replace", "add", "not_applicable", "review"]


class NoteSummary(View):
    id: str
    patient_name: str | None
    provider_name: str
    service_date: str
    status: NoteStatus
    lane: Lane | None
    lane_reason: LaneReason | None
    headline: str | None
    place_code: str
    visit_type: str
    flag_reason: str | None
    flagged_by: str | None
    due_at: str
    file_name: str
    assigned_to: str | None
    payer: str | None


class QueueRow(NoteSummary):
    assignee_name: str | None
    billed: list[str]
    suggested: list[str]
    em_action: EmAction | None
    impact_cents: int | None


class LaneCount(View):
    total: int
    due_soon: int


class LaneCounts(View):
    approve: LaneCount
    coder: LaneCount
    provider: LaneCount
    compliance: LaneCount


class ProviderReasonCounts(View):
    questions: LaneCount
    waiting_on_provider: LaneCount


class BatchProgress(View):
    id: str
    provider_name: str
    service_date: str
    place_code: str
    counts: dict[NoteStatus, int]


class TodaySummary(View):
    waiting: int
    due_soon: int
    lanes: LaneCounts
    provider_reasons: ProviderReasonCounts
    next_up: list[QueueRow]
    batches: list[BatchProgress]


class QueuePage(View):
    items: list[QueueRow]
    lanes: LaneCounts
    provider_reasons: ProviderReasonCounts
    total: int
    all_total: int
    failed: int
    page_size: int


class SearchResults(View):
    items: list[NoteSummary]
    limit: int


class ComplianceRow(QueueRow):
    flagged_by_name: str | None


class CompliancePattern(View):
    provider_name: str
    count: int


class ComplianceList(View):
    items: list[ComplianceRow]
    patterns: list[CompliancePattern]


class QueueViewFilters(View):
    lane: Lane | None
    reason: LaneReason | None
    assigned: str | None
    provider_id: str | None
    overdue: bool
    sort: QueueSort


class BuiltinView(View):
    key: Literal[BUILTIN_KEYS]
    filters: QueueViewFilters


class SavedView(View):
    id: str
    name: str
    filters: QueueViewFilters


class QueueViews(View):
    builtin: list[BuiltinView]
    saved: list[SavedView]
