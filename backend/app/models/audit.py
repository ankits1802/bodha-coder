from typing import Any

from sqlalchemy import BigInteger, Boolean, FetchedValue, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, LedgerMixin, one_of

ACCESS_DETAIL_LENGTH = 300
HASH_LENGTH = 64
NOTE_CHANGE_FIELDS = ("status", "flag", "payer", "assignee", "visit_type")


class ChainMixin:
    chain_seq: Mapped[int] = mapped_column(BigInteger, server_default=FetchedValue())
    prev_hash: Mapped[str] = mapped_column(String(HASH_LENGTH), server_default=FetchedValue())
    row_hash: Mapped[str] = mapped_column(String(HASH_LENGTH), server_default=FetchedValue())


class AccessLog(ChainMixin, LedgerMixin, Base):
    __tablename__ = "access_log"
    __table_args__ = (
        Index("ix_access_log_practice_time", "practice_id", "created_at"),
        Index("ix_access_log_practice_note", "practice_id", "note_id"),
        UniqueConstraint("practice_id", "chain_seq"),
        one_of("actor_kind", ("user", "provider", "system")),
    )
    practice_id: Mapped[str] = mapped_column(ForeignKey("practices.id"))
    actor_kind: Mapped[str] = mapped_column(String(8))
    actor_id: Mapped[str] = mapped_column(String(36))
    actor_name: Mapped[str] = mapped_column(String(120))
    action: Mapped[str] = mapped_column(String(40))
    note_id: Mapped[str | None] = mapped_column(String(36))
    detail: Mapped[str | None] = mapped_column(String(ACCESS_DETAIL_LENGTH))
    ip: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(300))


class Activity(ChainMixin, LedgerMixin, Base):
    __tablename__ = "activity"
    __table_args__ = (UniqueConstraint("chain_seq"),)
    actor_id: Mapped[str | None] = mapped_column(String(36))
    actor_name: Mapped[str] = mapped_column(String(120))
    action: Mapped[str] = mapped_column(String(40))
    practice_id: Mapped[str | None] = mapped_column(String(36), index=True)
    detail: Mapped[str | None] = mapped_column(String(300))
    changes: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB(none_as_null=True))


class AuditChainAnchor(LedgerMixin, Base):
    __tablename__ = "audit_chain_anchors"
    __table_args__ = (UniqueConstraint("chain", "through_seq"),)
    chain: Mapped[str] = mapped_column(String(80))
    through_seq: Mapped[int] = mapped_column(BigInteger)
    through_hash: Mapped[str] = mapped_column(String(HASH_LENGTH))
    rows_removed: Mapped[int] = mapped_column(Integer)


class NoteChange(LedgerMixin, Base):
    __tablename__ = "note_changes"
    __table_args__ = (one_of("field", NOTE_CHANGE_FIELDS),)
    note_id: Mapped[str] = mapped_column(ForeignKey("notes.id"), index=True)
    actor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    field: Mapped[str] = mapped_column(String(16))
    old_value: Mapped[str | None] = mapped_column(Text)
    new_value: Mapped[str | None] = mapped_column(Text)
    reason: Mapped[str | None] = mapped_column(Text)


class AnalysisFailure(LedgerMixin, Base):
    __tablename__ = "analysis_failures"
    analysis_id: Mapped[str] = mapped_column(ForeignKey("analyses.id"), index=True)
    attempt: Mapped[int] = mapped_column(Integer)
    error: Mapped[str] = mapped_column(String(300))
    retried: Mapped[bool] = mapped_column(Boolean)
