from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Computed,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, LedgerMixin, one_of, timestamp, utcnow

DEFAULT_CHECKS = {"em": True, "icd": True, "cdi": True, "audit": True, "mips": False, "hcc": False}
ROLES = ("hq", "admin", "coder", "cdi", "compliance", "biller", "viewer")
HQ_REALM = "hq"
PRACTICE_REALM = "practice"
REALMS = (HQ_REALM, PRACTICE_REALM)
REALM_OF_ROLE = f"CASE WHEN role = '{HQ_REALM}' THEN '{HQ_REALM}' ELSE '{PRACTICE_REALM}' END"
NOTE_STATUSES = ("queued", "reading", "ready", "failed", "approved", "exported", "voided")
VOIDED = "voided"
PRACTICE_STATUSES = ("trial", "active", "ended", "blocked", "closed", "purged")
CLOSED_STATUSES = ("closed", "purged")
ACCESS_LOG_MIN_YEARS = 7
ACCESS_LOG_MAX_YEARS = 10
LANES = ("approve", "coder", "provider", "compliance")
ANALYSIS_STATUSES = ("queued", "running", "succeeded", "failed", "superseded")
SUGGESTION_KINDS = (
    "em",
    "diagnosis",
    "modifier",
    "code_review",
    "cdi_gap",
    "cdi_query",
    "audit_risk",
    "audit_finding",
    "mips",
)
CHOICES = ("accept", "keep", "ask", "add", "skip")
CODE_SET_KINDS = ("billed", "final")
LANE_REASONS = (
    "flagged",
    "levels_too_high",
    "audit_risk",
    "waiting_on_provider",
    "code_changes",
    "questions",
    "matches",
)
DEFAULT_TIME_ZONE = "America/Chicago"


class Practice(IdMixin, Base):
    __tablename__ = "practices"
    __table_args__ = (
        one_of("status", PRACTICE_STATUSES),
        CheckConstraint(f"access_log_years >= {ACCESS_LOG_MIN_YEARS}", name="access_log_years_min"),
        CheckConstraint(
            f"(status IN ({', '.join(repr(item) for item in CLOSED_STATUSES)})) = (closed_at IS NOT NULL)",
            name="closed_when_closed_at",
        ),
    )
    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(16), default="trial")
    plan: Mapped[str] = mapped_column(String(16), default="trial")
    seats: Mapped[int] = mapped_column(Integer, default=10)
    renews_on: Mapped[date | None] = mapped_column(Date)
    setup: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    checks: Mapped[dict[str, bool]] = mapped_column(JSONB, default=lambda: dict(DEFAULT_CHECKS))
    mfa_roles: Mapped[list[str]] = mapped_column(JSONB, default=lambda: ["admin", "compliance"])
    idle_minutes: Mapped[int] = mapped_column(Integer, default=15)
    private_messages: Mapped[bool] = mapped_column(Boolean, default=True)
    time_zone: Mapped[str] = mapped_column(String(64), default=DEFAULT_TIME_ZONE)
    access_log_years: Mapped[int] = mapped_column(Integer, default=ACCESS_LOG_MIN_YEARS)
    intake: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    signup: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    closed_at: Mapped[datetime | None] = timestamp()
    closed_by: Mapped[str | None] = mapped_column(String(36))
    purged_at: Mapped[datetime | None] = timestamp()


class User(IdMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        one_of("role", ROLES),
        one_of("status", ("invited", "active", "blocked")),
        UniqueConstraint("email", "realm"),
        UniqueConstraint("id", "realm"),
    )
    __mapper_args__ = {"eager_defaults": True}
    practice_id: Mapped[str | None] = mapped_column(ForeignKey("practices.id"), index=True)
    email: Mapped[str] = mapped_column(String(254))
    name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(16))
    realm: Mapped[str] = mapped_column(String(16), Computed(REALM_OF_ROLE, persisted=True))
    status: Mapped[str] = mapped_column(String(16), default="invited")
    password_hash: Mapped[str | None] = mapped_column(String(100))
    mfa_secret: Mapped[str | None] = mapped_column(String(200))
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    mfa_last_step: Mapped[int | None] = mapped_column(Integer)
    notify_digest: Mapped[bool] = mapped_column(Boolean, default=True)
    token_version: Mapped[int] = mapped_column(Integer, default=0)
    last_active_at: Mapped[datetime | None] = timestamp()


class UserIdentity(IdMixin, Base):
    __tablename__ = "user_identities"
    __table_args__ = (
        UniqueConstraint("provider", "subject", "realm"),
        UniqueConstraint("user_id", "provider"),
        ForeignKeyConstraint(["user_id", "realm"], ["users.id", "users.realm"]),
    )
    user_id: Mapped[str] = mapped_column(String(36))
    realm: Mapped[str] = mapped_column(String(16), server_default=PRACTICE_REALM)
    provider: Mapped[str] = mapped_column(String(16))
    subject: Mapped[str] = mapped_column(String(255))


class UserToken(IdMixin, Base):
    __tablename__ = "user_tokens"
    __table_args__ = (one_of("purpose", ("invite", "reset")),)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    purpose: Mapped[str] = mapped_column(String(16))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = timestamp(nullable=False)
    used_at: Mapped[datetime | None] = timestamp()


class Session(IdMixin, Base):
    __tablename__ = "sessions"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    refresh_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = timestamp(nullable=False)
    last_used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    revoked_at: Mapped[datetime | None] = timestamp()
    user_agent: Mapped[str | None] = mapped_column(String(300))
    ip: Mapped[str | None] = mapped_column(String(64))


class RecoveryCode(IdMixin, Base):
    __tablename__ = "recovery_codes"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    code_hash: Mapped[str] = mapped_column(String(64))
    used_at: Mapped[datetime | None] = timestamp()


class RateEvent(IdMixin, Base):
    __tablename__ = "rate_events"
    __table_args__ = (
        Index("ix_rate_events_key", "bucket", "key_hash", "created_at"),
        Index("ix_rate_events_created_at", "created_at"),
    )
    bucket: Mapped[str] = mapped_column(String(24))
    key_hash: Mapped[str] = mapped_column(String(64))


class PlaceOfService(Base):
    __tablename__ = "places_of_service"
    code: Mapped[str] = mapped_column(String(2), primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Provider(IdMixin, Base):
    __tablename__ = "providers"
    __table_args__ = (one_of("channel", ("email", "sms")),)
    practice_id: Mapped[str] = mapped_column(ForeignKey("practices.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    credential: Mapped[str] = mapped_column(String(16))
    specialty: Mapped[str | None] = mapped_column(String(80))
    npi: Mapped[str | None] = mapped_column(String(10))
    place_code: Mapped[str | None] = mapped_column(ForeignKey("places_of_service.code"))
    email: Mapped[str | None] = mapped_column(String(254))
    phone: Mapped[str | None] = mapped_column(String(32))
    channel: Mapped[str] = mapped_column(String(8), default="email")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    auto_approve: Mapped[bool] = mapped_column(Boolean, default=False)


class Batch(LedgerMixin, Base):
    __tablename__ = "batches"
    __table_args__ = (one_of("source", ("upload", "intake")),)
    practice_id: Mapped[str] = mapped_column(ForeignKey("practices.id"), index=True)
    provider_id: Mapped[str] = mapped_column(ForeignKey("providers.id"))
    service_date: Mapped[date] = mapped_column(Date)
    place_code: Mapped[str] = mapped_column(ForeignKey("places_of_service.code"))
    visit_type: Mapped[str] = mapped_column(String(40))
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    source: Mapped[str] = mapped_column(String(12), default="upload")


class Note(IdMixin, Base):
    __tablename__ = "notes"
    __table_args__ = (
        Index(
            "uq_notes_practice_file",
            "practice_id",
            "file_sha256",
            unique=True,
            postgresql_where=text(f"status <> '{VOIDED}'"),
        ),
        Index("ix_notes_work", "practice_id", "status", "lane", "due_at"),
        one_of("status", NOTE_STATUSES),
        CheckConstraint("lane IS NULL OR lane IN ('approve', 'coder', 'provider', 'compliance')", name="lane_allowed"),
        CheckConstraint(
            "lane_reason IS NULL OR lane_reason IN (" + ", ".join(f"'{item}'" for item in LANE_REASONS) + ")",
            name="lane_reason_allowed",
        ),
    )
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    practice_id: Mapped[str] = mapped_column(ForeignKey("practices.id"))
    batch_id: Mapped[str] = mapped_column(ForeignKey("batches.id"), index=True)
    provider_id: Mapped[str] = mapped_column(ForeignKey("providers.id"), index=True)
    file_key: Mapped[str] = mapped_column(String(300))
    file_name: Mapped[str] = mapped_column(String(255))
    file_sha256: Mapped[str] = mapped_column(String(64))
    file_bytes: Mapped[int] = mapped_column(Integer)
    patient_name: Mapped[str | None] = mapped_column(String(200))
    patient_age: Mapped[int | None] = mapped_column(Integer)
    patient_sex: Mapped[str | None] = mapped_column(String(16))
    patient_birth_date: Mapped[date | None] = mapped_column(Date)
    service_date: Mapped[date] = mapped_column(Date)
    visit_type: Mapped[str] = mapped_column(String(40))
    place_code: Mapped[str] = mapped_column(String(2))
    status: Mapped[str] = mapped_column(String(16), default="queued")
    lane: Mapped[str | None] = mapped_column(String(16))
    lane_reason: Mapped[str | None] = mapped_column(String(24))
    headline: Mapped[str | None] = mapped_column(String(120))
    flag_reason: Mapped[str | None] = mapped_column(Text)
    flagged_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    compliance_cleared_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    current_analysis_id: Mapped[str | None] = mapped_column(String(36))
    approved_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    approved_at: Mapped[datetime | None] = timestamp()
    exported_at: Mapped[datetime | None] = timestamp()
    due_at: Mapped[datetime] = timestamp(nullable=False)
    assigned_to: Mapped[str | None] = mapped_column(ForeignKey("users.id"), index=True)
    payer: Mapped[str | None] = mapped_column(String(64))
    voided_at: Mapped[datetime | None] = timestamp()
    voided_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    void_reason: Mapped[str | None] = mapped_column(Text)
    status_before_void: Mapped[str | None] = mapped_column(String(16))


class NoteText(LedgerMixin, Base):
    __tablename__ = "note_texts"
    __table_args__ = (UniqueConstraint("note_id", "revision"), one_of("source", ("document", "addendum")))
    note_id: Mapped[str] = mapped_column(ForeignKey("notes.id"))
    revision: Mapped[int] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(12))
    text: Mapped[str] = mapped_column(Text)
    addendum_request_id: Mapped[str | None] = mapped_column(ForeignKey("addendum_requests.id"))


class Analysis(LedgerMixin, Base):
    __tablename__ = "analyses"
    __table_args__ = (
        UniqueConstraint("note_id", "revision"),
        Index("ix_analyses_queue", "status", "requested_at"),
        one_of("status", ANALYSIS_STATUSES),
    )
    note_id: Mapped[str] = mapped_column(ForeignKey("notes.id"))
    revision: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(24))
    status: Mapped[str] = mapped_column(String(12), default="queued")
    text_revision: Mapped[int | None] = mapped_column(Integer)
    context: Mapped[dict[str, Any]] = mapped_column(JSONB)
    model: Mapped[str | None] = mapped_column(String(60))
    prompt_version: Mapped[str | None] = mapped_column(String(20))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[datetime | None] = timestamp()
    finished_at: Mapped[datetime | None] = timestamp()
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    response_key: Mapped[str | None] = mapped_column(String(300))
    report: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    error: Mapped[str | None] = mapped_column(String(300))
    prompt_key: Mapped[str | None] = mapped_column(String(300))
    prompt_sha256: Mapped[str | None] = mapped_column(String(64))
    app_version: Mapped[str | None] = mapped_column(String(64))
    generation: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    document_key: Mapped[str | None] = mapped_column(String(300))


class Suggestion(LedgerMixin, Base):
    __tablename__ = "suggestions"
    __table_args__ = (UniqueConstraint("analysis_id", "key"), one_of("kind", SUGGESTION_KINDS))
    analysis_id: Mapped[str] = mapped_column(ForeignKey("analyses.id"))
    note_id: Mapped[str] = mapped_column(ForeignKey("notes.id"), index=True)
    kind: Mapped[str] = mapped_column(String(16))
    key: Mapped[str] = mapped_column(String(80))
    code_before: Mapped[str | None] = mapped_column(String(12))
    code_after: Mapped[str | None] = mapped_column(String(12))
    action: Mapped[str] = mapped_column(String(20))
    title: Mapped[str] = mapped_column(String(300))
    reasoning: Mapped[str] = mapped_column(Text)
    evidence: Mapped[list[str]] = mapped_column(JSONB, default=list)
    severity: Mapped[str | None] = mapped_column(String(12))
    detail: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


class Decision(LedgerMixin, Base):
    __tablename__ = "decisions"
    __table_args__ = (
        Index("ix_decisions_note_key", "note_id", "suggestion_key", "created_at"),
        one_of("choice", CHOICES),
    )
    note_id: Mapped[str] = mapped_column(ForeignKey("notes.id"))
    analysis_id: Mapped[str] = mapped_column(ForeignKey("analyses.id"))
    suggestion_key: Mapped[str] = mapped_column(String(80))
    choice: Mapped[str] = mapped_column(String(8))
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))


class CodeSet(LedgerMixin, Base):
    __tablename__ = "code_sets"
    __table_args__ = (UniqueConstraint("note_id", "kind", "revision"), one_of("kind", CODE_SET_KINDS))
    note_id: Mapped[str] = mapped_column(ForeignKey("notes.id"))
    kind: Mapped[str] = mapped_column(String(8))
    revision: Mapped[int] = mapped_column(Integer)
    codes: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    reason: Mapped[str] = mapped_column(String(40))
    actor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))


class AddendumRequest(IdMixin, Base):
    __tablename__ = "addendum_requests"
    __table_args__ = (
        one_of("status", ("sent", "answered", "expired", "cancelled")),
        one_of("channel", ("email", "sms")),
    )
    practice_id: Mapped[str] = mapped_column(ForeignKey("practices.id"), index=True)
    note_id: Mapped[str] = mapped_column(ForeignKey("notes.id"), index=True)
    analysis_id: Mapped[str] = mapped_column(ForeignKey("analyses.id"))
    provider_id: Mapped[str] = mapped_column(ForeignKey("providers.id"), index=True)
    questions: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    answers: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    addendum_text: Mapped[str | None] = mapped_column(Text)
    channel: Mapped[str] = mapped_column(String(8))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = timestamp(nullable=False)
    code_hash: Mapped[str | None] = mapped_column(String(64))
    code_expires_at: Mapped[datetime | None] = timestamp()
    code_attempts: Mapped[int] = mapped_column(Integer, default=0)
    hold_claim: Mapped[bool] = mapped_column(Boolean, default=True)
    remind_at: Mapped[datetime | None] = timestamp()
    escalated_at: Mapped[datetime | None] = timestamp()
    status: Mapped[str] = mapped_column(String(12), default="sent")
    sent_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    answered_at: Mapped[datetime | None] = timestamp()


class MipsList(IdMixin, Base):
    __tablename__ = "mips_lists"
    practice_id: Mapped[str] = mapped_column(ForeignKey("practices.id"), unique=True)
    measure_ids: Mapped[list[str]] = mapped_column(JSONB)
    updated_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class DemoRequest(IdMixin, Base):
    __tablename__ = "demo_requests"
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(254))
    organization: Mapped[str] = mapped_column(String(200))
    message: Mapped[str | None] = mapped_column(Text)
