from app.api.responses.base import NoteStatus, View

__all__ = ["BatchPage", "FilePreview", "MatchConfidence", "UploadResult", "UploadedBatch"]


class MatchConfidence(View):
    provider: float
    service_date: float
    place: float
    patient: float


class FilePreview(View):
    file_name: str
    cpt: str | None
    duplicate: bool
    provider_id: str | None
    service_date: str | None
    place_code: str | None
    patient_name: str | None
    confidence: MatchConfidence
    overall: float
    check: bool


class UploadResult(View):
    batch_id: str
    batch_ids: list[str]
    accepted: list[str]
    duplicates: list[str]


class UploadedBatch(View):
    id: str
    provider_name: str
    service_date: str
    place_code: str
    visit_type: str
    uploaded_by: str
    created_at: str
    counts: dict[NoteStatus, int]


class BatchPage(View):
    items: list[UploadedBatch]
    total: int
    offset: int
    page_size: int
