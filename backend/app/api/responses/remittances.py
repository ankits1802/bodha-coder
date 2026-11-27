from typing import Literal

from app.api.responses.base import View

__all__ = [
    "AppealDays",
    "AppealDraft",
    "RemittanceAdjustment",
    "RemittanceDetail",
    "RemittanceLine",
    "RemittanceListItem",
    "RemittancePage",
    "RemittanceSummary",
    "RemittanceUpload",
]

LineStatus = Literal["paid_as_billed", "downcoded", "denied", "matched", "unmatched"]


class RemittanceUpload(View):
    ids: list[str]
    counts: dict[LineStatus, int]


class RemittanceSummary(View):
    id: str
    file_name: str
    payer: str | None
    paid_on: str | None
    uploaded_by: str
    uploaded_at: str
    counts: dict[LineStatus, int]


class RemittanceListItem(RemittanceSummary):
    next_appeal_by: str | None


class RemittancePage(View):
    items: list[RemittanceListItem]
    total: int
    offset: int
    page_size: int


class RemittanceAdjustment(View):
    group: str
    reason: str
    cents: int


class RemittanceLine(View):
    id: str
    note_id: str | None
    claim_ref: str | None
    patient_name: str | None
    service_date: str | None
    billed_code: str | None
    paid_code: str | None
    billed_amount: int | None
    paid_amount: int | None
    adjustments: list[RemittanceAdjustment]
    status: LineStatus
    appeal_by: str | None


class RemittanceDetail(View):
    remittance: RemittanceSummary
    lines: list[RemittanceLine]


class AppealDraft(View):
    line_id: str
    note_id: str | None
    appeal_by: str
    text: str
    file_name: str
    defense_packet: str | None


class AppealDays(View):
    commercial: int
    medicare: int
    medicare_advantage: int
    medicaid: int
    other: int
