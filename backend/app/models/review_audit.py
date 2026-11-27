from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, LedgerMixin, one_of, timestamp

OVERRIDE_REASONS = (
    "documentation",
    "payer_policy",
    "provider_answer",
    "coding_guideline",
    "clinical_context",
    "other",
)
OVERRIDE_NOTE_LENGTH = 500
OVERRIDE_REASON_ALLOWED = (
    "override_reason IS NULL OR override_reason IN (" + ", ".join(f"'{reason}'" for reason in OVERRIDE_REASONS) + ")"
)
OTHER_NEEDS_NOTE = "override_reason IS DISTINCT FROM 'other' OR length(btrim(coalesce(override_note, ''))) > 0"
QUESTIONS_PURPOSE = "questions"
LEVEL_CHANGE_PURPOSE = "level_change"
REQUEST_PURPOSES = (QUESTIONS_PURPOSE, LEVEL_CHANGE_PURPOSE)
EXPORT_FORMATS = ("csv", "claim_lines_csv", "claim_lines_json")
ATTESTATION_ANSWERS = ("signed", "confirm", "disagree")
COMMENT_LENGTH = 2000
SNAPSHOT_SCHEMA_VERSION = 1


def override_checks() -> tuple[CheckConstraint, CheckConstraint]:
    return (
        CheckConstraint(OVERRIDE_REASON_ALLOWED, name="override_reason_allowed"),
        CheckConstraint(OTHER_NEEDS_NOTE, name="override_other_noted"),
    )


class ApprovedClaim(LedgerMixin, Base):
    __tablename__ = "approved_claims"
    __table_args__ = (UniqueConstraint("note_id", "revision"), Index("ix_approved_claims_practice", "practice_id"))
    practice_id: Mapped[str] = mapped_column(ForeignKey("practices.id"))
    note_id: Mapped[str] = mapped_column(ForeignKey("notes.id"))
    revision: Mapped[int] = mapped_column(Integer)
    final_code_set_id: Mapped[str] = mapped_column(ForeignKey("code_sets.id"))
    approved_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    approver_name: Mapped[str] = mapped_column(String(120))
    approver_role: Mapped[str] = mapped_column(String(16))
    approved_at: Mapped[datetime] = timestamp(nullable=False)
    analysis_id: Mapped[str | None] = mapped_column(ForeignKey("analyses.id"))
    model: Mapped[str | None] = mapped_column(String(60))
    prompt_version: Mapped[str | None] = mapped_column(String(20))
    text_revision_ids: Mapped[list[str]] = mapped_column(JSONB)
    document_key: Mapped[str] = mapped_column(String(300))
    document_sha256: Mapped[str] = mapped_column(String(64))
    schema_version: Mapped[int] = mapped_column(Integer)
    content: Mapped[dict[str, Any]] = mapped_column(JSONB)


class ClaimExport(LedgerMixin, Base):
    __tablename__ = "claim_exports"
    __table_args__ = (one_of("format", EXPORT_FORMATS), Index("ix_claim_exports_practice", "practice_id", "created_at"))
    practice_id: Mapped[str] = mapped_column(ForeignKey("practices.id"))
    format: Mapped[str] = mapped_column(String(20))
    again: Mapped[bool] = mapped_column(Boolean)
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    actor_name: Mapped[str] = mapped_column(String(120))
    actor_role: Mapped[str] = mapped_column(String(16))
    file_key: Mapped[str] = mapped_column(String(300))
    file_name: Mapped[str] = mapped_column(String(120))
    file_sha256: Mapped[str] = mapped_column(String(64))
    file_bytes: Mapped[int] = mapped_column(Integer)
    notes_count: Mapped[int] = mapped_column(Integer)
    ip: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(300))


class ClaimExportItem(LedgerMixin, Base):
    __tablename__ = "claim_export_items"
    __table_args__ = (UniqueConstraint("export_id", "note_id"), Index("ix_claim_export_items_note", "note_id"))
    practice_id: Mapped[str] = mapped_column(ForeignKey("practices.id"))
    export_id: Mapped[str] = mapped_column(ForeignKey("claim_exports.id"))
    note_id: Mapped[str] = mapped_column(ForeignKey("notes.id"))
    approved_claim_id: Mapped[str] = mapped_column(ForeignKey("approved_claims.id"))
    snapshot_revision: Mapped[int] = mapped_column(Integer)


class ProviderAttestation(LedgerMixin, Base):
    __tablename__ = "provider_attestations"
    __table_args__ = (
        one_of("purpose", REQUEST_PURPOSES),
        one_of("answer", ATTESTATION_ANSWERS),
        CheckConstraint("confirmed", name="confirmed_ticked"),
        Index("ix_provider_attestations_note", "note_id", "created_at"),
    )
    practice_id: Mapped[str] = mapped_column(ForeignKey("practices.id"))
    note_id: Mapped[str] = mapped_column(ForeignKey("notes.id"))
    request_id: Mapped[str] = mapped_column(ForeignKey("addendum_requests.id"))
    provider_id: Mapped[str] = mapped_column(ForeignKey("providers.id"))
    approved_claim_id: Mapped[str | None] = mapped_column(ForeignKey("approved_claims.id"))
    purpose: Mapped[str] = mapped_column(String(12))
    wording: Mapped[str] = mapped_column(Text)
    confirmed: Mapped[bool] = mapped_column(Boolean)
    text_revision_ids: Mapped[list[str]] = mapped_column(JSONB)
    shown: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(String(12))
    comment: Mapped[str | None] = mapped_column(String(COMMENT_LENGTH))
    ip: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(300))


class ReviewComment(LedgerMixin, Base):
    __tablename__ = "review_comments"
    __table_args__ = (Index("ix_review_comments_note", "note_id", "created_at"),)
    practice_id: Mapped[str] = mapped_column(ForeignKey("practices.id"))
    note_id: Mapped[str] = mapped_column(ForeignKey("notes.id"))
    finding_key: Mapped[str | None] = mapped_column(String(80))
    body: Mapped[str] = mapped_column(String(COMMENT_LENGTH))
    author_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    author_name: Mapped[str] = mapped_column(String(120))
    author_role: Mapped[str] = mapped_column(String(16))
    mentions: Mapped[list[str]] = mapped_column(JSONB)


class ReviewCommentRemoval(LedgerMixin, Base):
    __tablename__ = "review_comment_removals"
    practice_id: Mapped[str] = mapped_column(ForeignKey("practices.id"))
    note_id: Mapped[str] = mapped_column(ForeignKey("notes.id"), index=True)
    comment_id: Mapped[str] = mapped_column(ForeignKey("review_comments.id"), unique=True)
    removed_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    remover_name: Mapped[str] = mapped_column(String(120))
    remover_role: Mapped[str] = mapped_column(String(16))


class AuditPackage(LedgerMixin, Base):
    __tablename__ = "audit_packages"
    __table_args__ = (Index("ix_audit_packages_note", "note_id", "created_at"),)
    practice_id: Mapped[str] = mapped_column(ForeignKey("practices.id"))
    note_id: Mapped[str] = mapped_column(ForeignKey("notes.id"))
    file_key: Mapped[str] = mapped_column(String(300))
    file_sha256: Mapped[str] = mapped_column(String(64))
    file_bytes: Mapped[int] = mapped_column(Integer)
    file_count: Mapped[int] = mapped_column(Integer)
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    actor_name: Mapped[str] = mapped_column(String(120))
    actor_role: Mapped[str] = mapped_column(String(16))
    ip: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(300))
