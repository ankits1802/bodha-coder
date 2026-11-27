from app.api.responses.base import View

__all__ = ["BillingList", "BillingRow", "BillingSummary"]


class BillingRow(View):
    id: str
    patient_name: str | None
    service_date: str
    provider_name: str
    npi: str | None
    place_code: str
    codes: list[str]
    changed: int
    estimate: float | None
    approved_by: str
    approved_at: str | None
    exported_at: str | None
    cpt: list[str]
    icd10: list[str]


class BillingSummary(View):
    ready: int
    exported_today: int
    held_for_provider: int


class BillingList(View):
    items: list[BillingRow]
    summary: BillingSummary
    total: int
    offset: int
    page_size: int
    limit: int
