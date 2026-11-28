from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, LedgerMixin, utcnow

MEASURE_NAME_LENGTH = 80
MEASURE_IDENTIFIER_LENGTH = 20
MEASURE_SCOPE_LENGTH = 600
MEASURE_TO_MEET_LENGTH = 1000
MEASURE_KEY_FORMAT = "measure_key ~ '^P[0-9]{3}$'"


class PracticeMeasure(LedgerMixin, Base):
    __tablename__ = "practice_measures"
    __table_args__ = (
        UniqueConstraint("practice_id", "measure_key", "version"),
        CheckConstraint("version >= 1", name="version_min"),
        CheckConstraint(MEASURE_KEY_FORMAT, name="key_format"),
    )
    practice_id: Mapped[str] = mapped_column(ForeignKey("practices.id"))
    measure_key: Mapped[str] = mapped_column(String(4))
    version: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(MEASURE_NAME_LENGTH))
    identifier: Mapped[str | None] = mapped_column(String(MEASURE_IDENTIFIER_LENGTH))
    in_scope: Mapped[str] = mapped_column(String(MEASURE_SCOPE_LENGTH))
    out_of_scope: Mapped[str | None] = mapped_column(String(MEASURE_SCOPE_LENGTH))
    to_meet: Mapped[str] = mapped_column(String(MEASURE_TO_MEET_LENGTH))
    met_codes: Mapped[list[str]] = mapped_column(JSONB)
    not_met_codes: Mapped[list[str]] = mapped_column(JSONB)
    retired: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"))


class MipsList(IdMixin, Base):
    __tablename__ = "mips_lists"
    practice_id: Mapped[str] = mapped_column(ForeignKey("practices.id"), unique=True)
    measure_ids: Mapped[list[str]] = mapped_column(JSONB)
    updated_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
