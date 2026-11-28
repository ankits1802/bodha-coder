from datetime import date, datetime
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, Date, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, LedgerMixin, one_of, timestamp

EHR_URL_LENGTH = 500
EHR_CLIENT_ID_LENGTH = 200
EHR_SCOPES_LENGTH = 1000
EHR_KEY_SET_LENGTH = 32
FHIR_ID_LENGTH = 64
EHR_KEY_ALGORITHMS = ("RS384", "ES384")
EHR_CHANGES = ("saved", "paused", "resumed")
PULL_OUTCOMES = ("succeeded", "partial", "failed")
PULL_REASONS = (
    "no_key",
    "unsafe_address",
    "unreachable",
    "timeout",
    "too_large",
    "rate_limited",
    "redirected",
    "no_configuration",
    "token_refused",
    "server_refused",
    "server_error",
    "bad_response",
    "foreign_link",
)
DOCUMENT_OUTCOMES = ("accepted", "duplicate", "refused")
DOCUMENT_REASONS = (
    "not_final",
    "no_attachment",
    "unsupported_format",
    "too_large",
    "attachment_unavailable",
    "attachment_mismatch",
    "file_refused",
    "no_service_date",
    "future_service_date",
    "no_provider",
    "no_place",
    "foreign_reference",
    "upload_refused",
)


def _reason_allowed(values: tuple[str, ...]) -> CheckConstraint:
    allowed = ", ".join(repr(value) for value in values)
    return CheckConstraint(f"reason IS NULL OR reason IN ({allowed})", name="reason_allowed")


class EhrKey(LedgerMixin, Base):
    __tablename__ = "ehr_keys"
    __table_args__ = (
        Index("uq_ehr_keys_current", "practice_id", unique=True, postgresql_where=text("retired_at IS NULL")),
        Index("ix_ehr_keys_key_set", "key_set"),
        one_of("algorithm", EHR_KEY_ALGORITHMS),
    )
    practice_id: Mapped[str] = mapped_column(ForeignKey("practices.id"))
    key_set: Mapped[str] = mapped_column(String(EHR_KEY_SET_LENGTH))
    algorithm: Mapped[str] = mapped_column(String(8))
    public_jwk: Mapped[dict[str, Any]] = mapped_column(JSONB)
    private_key: Mapped[str] = mapped_column(Text)
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    retired_at: Mapped[datetime | None] = timestamp()
    retired_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))


class EhrConnection(LedgerMixin, Base):
    __tablename__ = "ehr_connections"
    __table_args__ = (UniqueConstraint("practice_id", "revision"), one_of("change", EHR_CHANGES))
    practice_id: Mapped[str] = mapped_column(ForeignKey("practices.id"))
    revision: Mapped[int] = mapped_column(Integer)
    base_url: Mapped[str] = mapped_column(String(EHR_URL_LENGTH))
    token_endpoint: Mapped[str] = mapped_column(String(EHR_URL_LENGTH))
    client_id: Mapped[str] = mapped_column(String(EHR_CLIENT_ID_LENGTH))
    scopes: Mapped[str] = mapped_column(String(EHR_SCOPES_LENGTH))
    note_types: Mapped[list[str]] = mapped_column(JSONB)
    start_date: Mapped[date] = mapped_column(Date)
    paused: Mapped[bool] = mapped_column(Boolean, default=False)
    change: Mapped[str] = mapped_column(String(12))
    changed_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))


class EhrPullRun(LedgerMixin, Base):
    __tablename__ = "ehr_pull_runs"
    __table_args__ = (
        Index("ix_ehr_pull_runs_practice", "practice_id", "created_at"),
        CheckConstraint(
            "outcome IS NULL OR outcome IN (" + ", ".join(repr(item) for item in PULL_OUTCOMES) + ")",
            name="outcome_allowed",
        ),
        _reason_allowed(PULL_REASONS),
        CheckConstraint("(outcome = 'failed') = (reason IS NOT NULL)", name="failed_with_reason"),
    )
    practice_id: Mapped[str] = mapped_column(ForeignKey("practices.id"))
    connection_id: Mapped[str] = mapped_column(ForeignKey("ehr_connections.id"))
    since: Mapped[datetime | None] = timestamp()
    finished_at: Mapped[datetime | None] = timestamp()
    outcome: Mapped[str | None] = mapped_column(String(12))
    reason: Mapped[str | None] = mapped_column(String(24))
    cursor: Mapped[datetime | None] = timestamp()
    pages: Mapped[int | None] = mapped_column(Integer)
    accepted: Mapped[int | None] = mapped_column(Integer)
    duplicates: Mapped[int | None] = mapped_column(Integer)
    refused: Mapped[int | None] = mapped_column(Integer)
    skipped: Mapped[int | None] = mapped_column(Integer)


class EhrDocument(LedgerMixin, Base):
    __tablename__ = "ehr_documents"
    __table_args__ = (
        Index("ix_ehr_documents_practice", "practice_id", "created_at"),
        Index("ix_ehr_documents_resource", "practice_id", "document_id"),
        Index("ix_ehr_documents_run", "run_id"),
        one_of("outcome", DOCUMENT_OUTCOMES),
        _reason_allowed(DOCUMENT_REASONS),
        CheckConstraint("(outcome = 'refused') = (reason IS NOT NULL)", name="refused_with_reason"),
    )
    practice_id: Mapped[str] = mapped_column(ForeignKey("practices.id"))
    run_id: Mapped[str] = mapped_column(ForeignKey("ehr_pull_runs.id"))
    document_id: Mapped[str] = mapped_column(String(FHIR_ID_LENGTH))
    document_version: Mapped[str] = mapped_column(String(FHIR_ID_LENGTH))
    encounter_id: Mapped[str | None] = mapped_column(String(FHIR_ID_LENGTH))
    practitioner_id: Mapped[str | None] = mapped_column(String(FHIR_ID_LENGTH))
    outcome: Mapped[str] = mapped_column(String(12))
    reason: Mapped[str | None] = mapped_column(String(24))
    note_id: Mapped[str | None] = mapped_column(ForeignKey("notes.id"))
    file_sha256: Mapped[str | None] = mapped_column(String(64))
    file_bytes: Mapped[int | None] = mapped_column(Integer)
