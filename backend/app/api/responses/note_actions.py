from app.api.responses.base import Lane, NoteStatus, View

__all__ = [
    "ApprovedNotes",
    "AssignedNotes",
    "ClaimDiagnosis",
    "ClaimPointers",
    "ComplianceOutcome",
    "DeletedNotes",
    "NoteLane",
    "NotePayer",
    "NoteState",
    "PointerLine",
    "QueuedNotes",
    "RequestCancelled",
    "RequestCreated",
]


class NoteState(View):
    status: NoteStatus


class NoteLane(View):
    lane: Lane | None


class ComplianceOutcome(View):
    status: NoteStatus
    lane: Lane | None


class RequestCancelled(View):
    lane: str


class NotePayer(View):
    payer: str | None


class ApprovedNotes(View):
    approved: list[str]


class AssignedNotes(View):
    assigned: list[str]


class DeletedNotes(View):
    deleted: list[str]


class QueuedNotes(View):
    queued: list[str]


class RequestCreated(View):
    request_id: str


class ClaimDiagnosis(View):
    code: str
    letter: str | None


class PointerLine(View):
    code: str
    label: str
    pointers: list[str]
    stored: bool


class ClaimPointers(View):
    diagnoses: list[ClaimDiagnosis]
    lines: list[PointerLine]
