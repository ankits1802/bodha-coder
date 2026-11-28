from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, LedgerMixin, one_of, timestamp

LOCAL_PART_LENGTH = 32
SENDER_LENGTH = 254
MESSAGE_KEY_LENGTH = 128
SENDER_KINDS = ("address", "domain")
MESSAGE_OUTCOMES = ("accepted", "refused", "test")
REFUSAL_REASONS = (
    "unknown_address",
    "retired_address",
    "practice_closed",
    "failed_scan",
    "not_authenticated",
    "sender_not_allowed",
    "no_pdf",
    "too_many_files",
    "files_refused",
)


class IntakeAddress(LedgerMixin, Base):
    __tablename__ = "intake_addresses"
    __table_args__ = (
        Index("uq_intake_addresses_current", "practice_id", unique=True, postgresql_where=text("retired_at IS NULL")),
        Index("ix_intake_addresses_practice", "practice_id", "created_at"),
    )
    practice_id: Mapped[str] = mapped_column(ForeignKey("practices.id"))
    local_part: Mapped[str] = mapped_column(String(LOCAL_PART_LENGTH), unique=True)
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    retired_at: Mapped[datetime | None] = timestamp()
    retired_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))


class IntakeSender(LedgerMixin, Base):
    __tablename__ = "intake_senders"
    __table_args__ = (
        Index(
            "uq_intake_senders_current",
            "practice_id",
            "pattern",
            unique=True,
            postgresql_where=text("removed_at IS NULL"),
        ),
        one_of("kind", SENDER_KINDS),
    )
    practice_id: Mapped[str] = mapped_column(ForeignKey("practices.id"))
    pattern: Mapped[str] = mapped_column(String(SENDER_LENGTH))
    kind: Mapped[str] = mapped_column(String(8))
    added_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    removed_at: Mapped[datetime | None] = timestamp()
    removed_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))


class IntakeMessage(LedgerMixin, Base):
    __tablename__ = "intake_messages"
    __table_args__ = (
        UniqueConstraint("message_key", "address_id", postgresql_nulls_not_distinct=True),
        Index("ix_intake_messages_practice", "practice_id", "created_at"),
        one_of("outcome", MESSAGE_OUTCOMES),
        CheckConstraint(
            f"reason IS NULL OR reason IN ({', '.join(repr(item) for item in REFUSAL_REASONS)})",
            name="reason_allowed",
        ),
        CheckConstraint("(outcome = 'refused') = (reason IS NOT NULL)", name="refused_with_reason"),
    )
    message_key: Mapped[str] = mapped_column(String(MESSAGE_KEY_LENGTH))
    practice_id: Mapped[str | None] = mapped_column(ForeignKey("practices.id"))
    address_id: Mapped[str | None] = mapped_column(ForeignKey("intake_addresses.id"))
    received_at: Mapped[datetime] = timestamp(nullable=False)
    sender: Mapped[str | None] = mapped_column(String(SENDER_LENGTH))
    outcome: Mapped[str] = mapped_column(String(12))
    reason: Mapped[str | None] = mapped_column(String(24))
    accepted_files: Mapped[int] = mapped_column(Integer, default=0)
    refused_files: Mapped[int] = mapped_column(Integer, default=0)
    files: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    verdicts: Mapped[dict[str, str]] = mapped_column(JSONB, default=dict)


class IntakeTest(LedgerMixin, Base):
    __tablename__ = "intake_tests"
    __table_args__ = (Index("ix_intake_tests_address", "address_id", "created_at"),)
    practice_id: Mapped[str] = mapped_column(ForeignKey("practices.id"))
    address_id: Mapped[str] = mapped_column(ForeignKey("intake_addresses.id"))
    token_hash: Mapped[str] = mapped_column(String(64))
    requested_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    message_id: Mapped[str | None] = mapped_column(ForeignKey("intake_messages.id"))
    arrived_at: Mapped[datetime | None] = timestamp()
