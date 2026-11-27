from app.api.responses.base import NoteStatus, View

__all__ = ["BatchPage", "FilePreview", "UploadResult", "UploadedBatch"]


class FilePreview(View):
    file_name: str
    service_date: str | None
    patient_name: str | None
    cpt: str | None


class UploadResult(View):
    batch_id: str
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
