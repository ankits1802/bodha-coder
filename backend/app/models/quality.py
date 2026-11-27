from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, one_of, timestamp


class AuditSample(IdMixin, Base):
    __tablename__ = "audit_samples"
    __table_args__ = (one_of("status", ("open", "done")), one_of("purpose", ("audit", "training")))
    practice_id: Mapped[str] = mapped_column(ForeignKey("practices.id"), index=True)
    note_id: Mapped[str] = mapped_column(ForeignKey("notes.id"), index=True)
    analysis_id: Mapped[str | None] = mapped_column(ForeignKey("analyses.id"))
    reviewer_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    purpose: Mapped[str] = mapped_column(String(12), default="audit")
    status: Mapped[str] = mapped_column(String(8), default="open")
    answer: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    result: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    completed_at: Mapped[datetime | None] = timestamp()


class EvalCase(IdMixin, Base):
    __tablename__ = "eval_cases"
    __table_args__ = (UniqueConstraint("practice_id", "note_id"),)
    practice_id: Mapped[str] = mapped_column(ForeignKey("practices.id"), index=True)
    note_id: Mapped[str] = mapped_column(ForeignKey("notes.id"))
    expected: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"))


class EvalRun(IdMixin, Base):
    __tablename__ = "eval_runs"
    __table_args__ = (one_of("status", ("queued", "running", "done", "failed")),)
    practice_id: Mapped[str] = mapped_column(ForeignKey("practices.id"), index=True)
    model: Mapped[str] = mapped_column(String(80))
    prompt_version: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(8), default="queued")
    results: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    summary: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    requested_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    finished_at: Mapped[datetime | None] = timestamp()
