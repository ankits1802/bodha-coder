from app.api.responses.base import RequestStatus, View
from app.api.responses.notes import AddendumQuestion, TextRevision
from app.api.responses.review_records import RequestPurpose
from app.api.responses.signatures import SignatureView

__all__ = [
    "CodeSent",
    "LevelChangeView",
    "OtherRequest",
    "ProviderRequest",
    "ProviderToken",
    "RequestPatient",
    "RespondResult",
]


class CodeSent(View):
    sent_to: str


class ProviderToken(View):
    provider_token: str


class RequestPatient(View):
    name: str | None
    age: int | None
    sex: str | None


class LevelChangeView(View):
    billed: str | None
    approved: str | None
    shown: str


class ProviderRequest(View):
    practice_name: str
    provider_name: str
    status: RequestStatus
    patient: RequestPatient
    service_date: str
    visit_type: str
    place_code: str
    place_name: str | None
    requested_by: str | None
    requested_at: str
    answered_at: str | None
    expires_at: str
    questions: list[AddendumQuestion]
    texts: list[TextRevision]
    addendum_text: str | None
    purpose: RequestPurpose
    attestation: str
    level_change: LevelChangeView | None
    signature: SignatureView | None


class RespondResult(View):
    status: RequestStatus
    addendum_text: str


class OtherRequest(View):
    id: str
    patient_name: str | None
    service_date: str
    sent_at: str
    questions: int
