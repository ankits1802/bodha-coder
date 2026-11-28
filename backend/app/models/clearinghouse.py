from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, LedgerMixin, one_of, timestamp

TRANSPORTS = ("sftp", "portal")
USAGES = ("test", "production")
ID_QUALIFIERS = ("01", "14", "20", "27", "28", "29", "30", "33", "ZZ")
AUTH_KINDS = ("password", "key")
DELIVERIES = ("sftp", "download")
DELIVERY_OUTCOMES = ("delivered", "failed", "downloaded")
ACK_SOURCES = ("sftp", "upload")
ACK_FILE_KINDS = ("999", "277CA", "other", "unreadable", "duplicate")
ACK_KINDS = ("999", "277CA")
ACK_LEVELS = ("file", "claim")
ACK_OUTCOMES = ("accepted", "rejected", "pending")
RELATIONSHIPS = ("18", "01", "19", "G8")
PATIENT_SEXES = ("F", "M", "U")
SELF_RELATIONSHIP = "18"
CLAIM_REF_LENGTH = 20
SFTP_COMPLETE = (
    "transport <> 'sftp' OR (host IS NOT NULL AND port IS NOT NULL AND username IS NOT NULL AND auth_kind IS NOT NULL"
    " AND secret IS NOT NULL AND host_key_sha256 IS NOT NULL AND outbound_folder IS NOT NULL"
    " AND inbound_folder IS NOT NULL)"
)
SUBSCRIBER_NAMED = "relationship = '18' OR (subscriber_last IS NOT NULL AND subscriber_first IS NOT NULL)"


class ClearinghouseConnection(LedgerMixin, Base):
    __tablename__ = "clearinghouse_connections"
    __table_args__ = (
        Index(
            "uq_clearinghouse_connections_current",
            "practice_id",
            unique=True,
            postgresql_where=text("retired_at IS NULL"),
        ),
        Index("ix_clearinghouse_connections_practice", "practice_id", "created_at"),
        one_of("transport", TRANSPORTS),
        one_of("usage", USAGES),
        one_of("sender_qualifier", ID_QUALIFIERS),
        one_of("receiver_qualifier", ID_QUALIFIERS),
        CheckConstraint("auth_kind IS NULL OR auth_kind IN ('password', 'key')", name="auth_kind_allowed"),
        CheckConstraint("port IS NULL OR port BETWEEN 1 AND 65535", name="port_range"),
        CheckConstraint(SFTP_COMPLETE, name="sftp_complete"),
    )
    practice_id: Mapped[str] = mapped_column(ForeignKey("practices.id"))
    name: Mapped[str] = mapped_column(String(80))
    transport: Mapped[str] = mapped_column(String(8))
    usage: Mapped[str] = mapped_column(String(12))
    sender_qualifier: Mapped[str] = mapped_column(String(2))
    sender_id: Mapped[str] = mapped_column(String(15))
    receiver_qualifier: Mapped[str] = mapped_column(String(2))
    receiver_id: Mapped[str] = mapped_column(String(15))
    receiver_name: Mapped[str] = mapped_column(String(60))
    host: Mapped[str | None] = mapped_column(String(253))
    port: Mapped[int | None] = mapped_column(Integer)
    username: Mapped[str | None] = mapped_column(String(128))
    auth_kind: Mapped[str | None] = mapped_column(String(8))
    secret: Mapped[str | None] = mapped_column(Text)
    host_key_sha256: Mapped[str | None] = mapped_column(String(80))
    outbound_folder: Mapped[str | None] = mapped_column(String(255))
    inbound_folder: Mapped[str | None] = mapped_column(String(255))
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    retired_at: Mapped[datetime | None] = timestamp()
    retired_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))


class ClaimDetail(LedgerMixin, Base):
    __tablename__ = "claim_details"
    __table_args__ = (
        UniqueConstraint("note_id", "revision"),
        Index("ix_claim_details_practice", "practice_id", "created_at"),
        one_of("relationship", RELATIONSHIPS),
        one_of("patient_sex", PATIENT_SEXES),
        CheckConstraint(SUBSCRIBER_NAMED, name="subscriber_named"),
    )
    practice_id: Mapped[str] = mapped_column(ForeignKey("practices.id"))
    note_id: Mapped[str] = mapped_column(ForeignKey("notes.id"))
    revision: Mapped[int] = mapped_column(Integer)
    patient_last: Mapped[str] = mapped_column(String(60))
    patient_first: Mapped[str] = mapped_column(String(35))
    patient_birth_date: Mapped[date] = mapped_column(Date)
    patient_sex: Mapped[str] = mapped_column(String(1))
    street: Mapped[str] = mapped_column(String(55))
    street_2: Mapped[str | None] = mapped_column(String(55))
    city: Mapped[str] = mapped_column(String(30))
    state: Mapped[str] = mapped_column(String(2))
    zip_code: Mapped[str] = mapped_column(String(9))
    relationship: Mapped[str] = mapped_column(String(2))
    member_id: Mapped[str] = mapped_column(String(80))
    group_number: Mapped[str | None] = mapped_column(String(50))
    subscriber_last: Mapped[str | None] = mapped_column(String(60))
    subscriber_first: Mapped[str | None] = mapped_column(String(35))
    confirmed_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    confirmer_name: Mapped[str] = mapped_column(String(120))
    confirmer_role: Mapped[str] = mapped_column(String(16))


class ClaimSubmission(LedgerMixin, Base):
    __tablename__ = "claim_submissions"
    __table_args__ = (
        UniqueConstraint("sender_qualifier", "sender_id", "control_number"),
        Index("ix_claim_submissions_practice", "practice_id", "created_at"),
        one_of("delivery", DELIVERIES),
        one_of("usage", USAGES),
        CheckConstraint("control_number BETWEEN 1 AND 999999999", name="control_number_range"),
    )
    practice_id: Mapped[str] = mapped_column(ForeignKey("practices.id"))
    connection_id: Mapped[str] = mapped_column(ForeignKey("clearinghouse_connections.id"))
    delivery: Mapped[str] = mapped_column(String(8))
    usage: Mapped[str] = mapped_column(String(12))
    sender_qualifier: Mapped[str] = mapped_column(String(2))
    sender_id: Mapped[str] = mapped_column(String(15))
    receiver_id: Mapped[str] = mapped_column(String(15))
    control_number: Mapped[int] = mapped_column(Integer)
    batch_ref: Mapped[str] = mapped_column(String(32), unique=True)
    file_key: Mapped[str] = mapped_column(String(300))
    file_sha256: Mapped[str] = mapped_column(String(64))
    file_bytes: Mapped[int] = mapped_column(Integer)
    claims_count: Mapped[int] = mapped_column(Integer)
    total_cents: Mapped[int] = mapped_column(BigInteger)
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    actor_name: Mapped[str] = mapped_column(String(120))
    actor_role: Mapped[str] = mapped_column(String(16))
    ip: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(300))


class ClaimSubmissionItem(LedgerMixin, Base):
    __tablename__ = "claim_submission_items"
    __table_args__ = (
        UniqueConstraint("submission_id", "note_id"),
        UniqueConstraint("claim_ref", "submission_id"),
        Index("ix_claim_submission_items_note", "note_id", "created_at"),
        Index("ix_claim_submission_items_practice", "practice_id", "claim_ref"),
    )
    practice_id: Mapped[str] = mapped_column(ForeignKey("practices.id"))
    submission_id: Mapped[str] = mapped_column(ForeignKey("claim_submissions.id"))
    note_id: Mapped[str] = mapped_column(ForeignKey("notes.id"))
    approved_claim_id: Mapped[str] = mapped_column(ForeignKey("approved_claims.id"))
    snapshot_revision: Mapped[int] = mapped_column(Integer)
    claim_detail_id: Mapped[str] = mapped_column(ForeignKey("claim_details.id"))
    payer_key: Mapped[str] = mapped_column(String(36))
    claim_ref: Mapped[str] = mapped_column(String(CLAIM_REF_LENGTH))
    charge_cents: Mapped[int] = mapped_column(BigInteger)
    lines_count: Mapped[int] = mapped_column(Integer)


class ClaimDelivery(LedgerMixin, Base):
    __tablename__ = "claim_deliveries"
    __table_args__ = (
        Index("ix_claim_deliveries_submission", "submission_id", "created_at"),
        one_of("outcome", DELIVERY_OUTCOMES),
        CheckConstraint("(outcome = 'failed') = (error IS NOT NULL)", name="failed_with_error"),
    )
    practice_id: Mapped[str] = mapped_column(ForeignKey("practices.id"))
    submission_id: Mapped[str] = mapped_column(ForeignKey("claim_submissions.id"))
    outcome: Mapped[str] = mapped_column(String(12))
    remote_name: Mapped[str | None] = mapped_column(String(120))
    error: Mapped[str | None] = mapped_column(String(300))
    actor_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    actor_name: Mapped[str] = mapped_column(String(120))


class ClaimAckFile(LedgerMixin, Base):
    __tablename__ = "claim_ack_files"
    __table_args__ = (
        Index("ix_claim_ack_files_practice", "practice_id", "created_at"),
        Index("ix_claim_ack_files_sha256", "practice_id", "file_sha256"),
        Index("ix_claim_ack_files_remote", "practice_id", "remote_name_sha256"),
        one_of("source", ACK_SOURCES),
        one_of("kind", ACK_FILE_KINDS),
        CheckConstraint("(source = 'upload') = (uploaded_by IS NOT NULL)", name="uploaded_by_a_person"),
    )
    practice_id: Mapped[str] = mapped_column(ForeignKey("practices.id"))
    connection_id: Mapped[str | None] = mapped_column(ForeignKey("clearinghouse_connections.id"))
    source: Mapped[str] = mapped_column(String(8))
    kind: Mapped[str] = mapped_column(String(12))
    remote_name_sha256: Mapped[str | None] = mapped_column(String(64))
    file_key: Mapped[str] = mapped_column(String(300))
    file_sha256: Mapped[str] = mapped_column(String(64))
    file_bytes: Mapped[int] = mapped_column(Integer)
    error: Mapped[str | None] = mapped_column(String(300))
    uploaded_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))


class ClaimAck(LedgerMixin, Base):
    __tablename__ = "claim_acks"
    __table_args__ = (
        Index("ix_claim_acks_submission", "submission_id", "created_at"),
        Index("ix_claim_acks_note", "note_id", "created_at"),
        Index("ix_claim_acks_file", "file_id"),
        one_of("kind", ACK_KINDS),
        one_of("level", ACK_LEVELS),
        one_of("outcome", ACK_OUTCOMES),
        CheckConstraint("level = 'file' OR item_id IS NOT NULL OR submission_id IS NULL", name="claim_level_item"),
    )
    practice_id: Mapped[str] = mapped_column(ForeignKey("practices.id"))
    file_id: Mapped[str] = mapped_column(ForeignKey("claim_ack_files.id"))
    kind: Mapped[str] = mapped_column(String(6))
    level: Mapped[str] = mapped_column(String(6))
    outcome: Mapped[str] = mapped_column(String(10))
    submission_id: Mapped[str | None] = mapped_column(ForeignKey("claim_submissions.id"))
    item_id: Mapped[str | None] = mapped_column(ForeignKey("claim_submission_items.id"))
    note_id: Mapped[str | None] = mapped_column(ForeignKey("notes.id"))
    claim_ref: Mapped[str | None] = mapped_column(String(CLAIM_REF_LENGTH))
    payer_claim_number: Mapped[str | None] = mapped_column(String(50))
    reasons: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
