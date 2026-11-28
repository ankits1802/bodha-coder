from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.accounts import PRACTICE_MEMBER_ROLES
from app.models.base import Base, LedgerMixin, one_of

USAGE_KINDS = ("task", "stall")
USAGE_TASKS = ("note_review", "queue", "upload", "billing_export")
USAGE_OUTCOMES = ("completed", "left")
USAGE_STEPS = (
    "summary",
    "note",
    "findings",
    "claim",
    "dialog",
    "history",
    "navigation",
    "queue",
    "upload",
    "billing",
)
USAGE_COUNTS = ("key_inputs", "pointer_inputs", "key_decisions", "pointer_decisions")
USAGE_COUNTS_CHECK = " AND ".join(f"{name} >= 0" for name in USAGE_COUNTS)


class UsageEvent(LedgerMixin, Base):
    __tablename__ = "usage_events"
    __table_args__ = (
        one_of("role", PRACTICE_MEMBER_ROLES),
        one_of("kind", USAGE_KINDS),
        one_of("task", USAGE_TASKS),
        one_of("step", USAGE_STEPS),
        one_of("outcome", USAGE_OUTCOMES),
        CheckConstraint("(kind = 'task') = (outcome IS NOT NULL)", name="task_outcome"),
        CheckConstraint("(kind = 'stall') = (step IS NOT NULL)", name="stall_step"),
        CheckConstraint("duration_ms >= 0 AND coalesce(first_decision_ms, 0) >= 0", name="durations_min"),
        CheckConstraint(USAGE_COUNTS_CHECK, name="counts_min"),
        UniqueConstraint("user_id", "client_event_id"),
        Index("ix_usage_events_practice", "practice_id", "created_at"),
        Index("ix_usage_events_created", "created_at"),
    )
    practice_id: Mapped[str] = mapped_column(ForeignKey("practices.id"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    role: Mapped[str] = mapped_column(String(16))
    client_event_id: Mapped[str] = mapped_column(String(36))
    kind: Mapped[str] = mapped_column(String(8))
    task: Mapped[str] = mapped_column(String(16))
    step: Mapped[str | None] = mapped_column(String(16))
    outcome: Mapped[str | None] = mapped_column(String(12))
    duration_ms: Mapped[int] = mapped_column(Integer)
    first_decision_ms: Mapped[int | None] = mapped_column(Integer)
    key_inputs: Mapped[int] = mapped_column(Integer, default=0)
    pointer_inputs: Mapped[int] = mapped_column(Integer, default=0)
    key_decisions: Mapped[int] = mapped_column(Integer, default=0)
    pointer_decisions: Mapped[int] = mapped_column(Integer, default=0)
