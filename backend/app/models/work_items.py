from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, one_of, timestamp

INBOX_KINDS = (
    "provider_answered",
    "level_disagreed",
    "request_expired",
    "mentioned",
    "training_assigned",
    "payment_failed",
    "plan_ending",
    "compliance_returned",
    "join_requested",
    "claim_rejected",
)
INBOX_KIND_LENGTH = 24
QUEUE_VIEW_NAME_LENGTH = 60


class InboxItem(IdMixin, Base):
    __tablename__ = "inbox_items"
    __table_args__ = (
        Index("ix_inbox_items_recipient", "user_id", "practice_id", "created_at"),
        one_of("kind", INBOX_KINDS),
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    practice_id: Mapped[str] = mapped_column(ForeignKey("practices.id"))
    kind: Mapped[str] = mapped_column(String(INBOX_KIND_LENGTH))
    note_id: Mapped[str | None] = mapped_column(String(36))
    actor_id: Mapped[str | None] = mapped_column(String(36))
    actor_name: Mapped[str] = mapped_column(String(120))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    read_at: Mapped[datetime | None] = timestamp()


class QueueView(IdMixin, Base):
    __tablename__ = "queue_views"
    __table_args__ = (UniqueConstraint("user_id", "practice_id", "name"),)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    practice_id: Mapped[str] = mapped_column(ForeignKey("practices.id"))
    name: Mapped[str] = mapped_column(String(QUEUE_VIEW_NAME_LENGTH))
    filters: Mapped[dict[str, Any]] = mapped_column(JSONB)
