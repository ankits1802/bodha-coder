from typing import Literal

from app.api.responses.base import View
from app.models import ATTESTATION_ANSWERS, EXPORT_FORMATS, OVERRIDE_REASONS, REQUEST_PURPOSES

__all__ = [
    "AttestationRecord",
    "CommentMention",
    "CommentPerson",
    "CommentRemoval",
    "ExportPage",
    "ExportRecord",
    "LevelChangeResult",
    "NoteComment",
    "NoteComments",
    "NoteExportRecord",
    "OverrideReason",
    "OverrideView",
    "RequestPurpose",
    "ReviewSettings",
    "SnapshotRecord",
]

OverrideReason = Literal[OVERRIDE_REASONS]
RequestPurpose = Literal[REQUEST_PURPOSES]
ExportFormat = Literal[EXPORT_FORMATS]


class OverrideView(View):
    reason: OverrideReason
    note: str | None


class SnapshotRecord(View):
    id: str
    revision: int
    approved_at: str
    approver_name: str
    approver_role: str
    codes: list[str]
    billed: list[str]
    decisions: int
    analysis_id: str | None
    model: str | None
    prompt_version: str | None
    text_revisions: int
    document_sha256: str


class ExportRecord(View):
    id: str
    at: str
    by: str
    role: str
    format: ExportFormat
    again: bool
    notes: int
    file_name: str
    sha256: str
    bytes: int


class NoteExportRecord(ExportRecord):
    snapshot_revision: int


class ExportPage(View):
    items: list[ExportRecord]
    total: int
    offset: int
    page_size: int


class AttestationRecord(View):
    id: str
    at: str
    provider: str
    purpose: RequestPurpose
    answer: Literal[ATTESTATION_ANSWERS]
    comment: str | None
    wording: str
    shown: str
    text_revisions: int
    ip: str | None
    user_agent: str | None


class CommentMention(View):
    id: str
    name: str


class CommentRemoval(View):
    by: str
    role: str
    at: str


class NoteComment(View):
    id: str
    finding_key: str | None
    body: str
    author_name: str
    author_role: str
    at: str
    mentions: list[CommentMention]
    removed: CommentRemoval | None
    can_remove: bool


class NoteComments(View):
    items: list[NoteComment]


class CommentPerson(View):
    id: str
    name: str
    role: str


class ReviewSettings(View):
    confirm_level_changes: bool
    hold_until_confirmed: bool


class LevelChangeResult(View):
    status: Literal["sent", "answered", "expired", "cancelled"]
    answer: Literal["confirm", "disagree"]
