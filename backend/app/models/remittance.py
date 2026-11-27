from datetime import date
from typing import Any

from sqlalchemy import Date, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, one_of


class Remittance(IdMixin, Base):
    __tablename__ = "remittances"
    practice_id: Mapped[str] = mapped_column(ForeignKey("practices.id"), index=True)
    file_key: Mapped[str] = mapped_column(String(300))
    file_name: Mapped[str] = mapped_column(String(255))
    payer: Mapped[str | None] = mapped_column(String(120))
    paid_on: Mapped[date | None] = mapped_column(Date)
    uploaded_by: Mapped[str] = mapped_column(ForeignKey("users.id"))


class RemittanceLine(IdMixin, Base):
    __tablename__ = "remittance_lines"
    __table_args__ = (one_of("status", ("matched", "unmatched", "downcoded", "denied", "paid_as_billed")),)
    remittance_id: Mapped[str] = mapped_column(ForeignKey("remittances.id"), index=True)
    note_id: Mapped[str | None] = mapped_column(ForeignKey("notes.id"), index=True)
    claim_ref: Mapped[str | None] = mapped_column(String(80))
    patient_name: Mapped[str | None] = mapped_column(String(200))
    service_date: Mapped[date | None] = mapped_column(Date)
    billed_code: Mapped[str | None] = mapped_column(String(16))
    paid_code: Mapped[str | None] = mapped_column(String(16))
    billed_amount: Mapped[int | None] = mapped_column(Integer)
    paid_amount: Mapped[int | None] = mapped_column(Integer)
    adjustments: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    status: Mapped[str] = mapped_column(String(16), default="unmatched")
    appeal_by: Mapped[date | None] = mapped_column(Date)
