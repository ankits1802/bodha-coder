from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, one_of, timestamp

SIGNATURE_SOURCES = ("drawn", "typed", "uploaded")
SIGNING_EVENTS = ("approval", "compliance_decision", "provider_addendum", "provider_level_change", "agreement")
SIGNER_KINDS = ("user", "provider")
SEAL_SCHEMA_VERSION = 1
SIGNER_NAME_LENGTH = 120
ONE_OWNER = "(user_id IS NULL) <> (provider_id IS NULL)"
PROVIDER_IN_PRACTICE = "provider_id IS NULL OR practice_id IS NOT NULL"
ONE_SIGNER = "(signer_user_id IS NULL) <> (signer_provider_id IS NULL)"


def owner_checks() -> tuple[CheckConstraint, CheckConstraint]:
    return (
        CheckConstraint(ONE_OWNER, name="one_owner"),
        CheckConstraint(PROVIDER_IN_PRACTICE, name="provider_in_practice"),
    )


class Signature(IdMixin, Base):
    __tablename__ = "signatures"
    __table_args__ = (
        one_of("source", SIGNATURE_SOURCES),
        *owner_checks(),
        Index("ix_signatures_user", "user_id", "created_at"),
        Index("ix_signatures_provider", "provider_id", "created_at"),
    )
    practice_id: Mapped[str | None] = mapped_column(ForeignKey("practices.id"))
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    provider_id: Mapped[str | None] = mapped_column(ForeignKey("providers.id"))
    source: Mapped[str] = mapped_column(String(12))
    typed_name: Mapped[str] = mapped_column(String(SIGNER_NAME_LENGTH))
    file_key: Mapped[str] = mapped_column(String(300))
    sha256: Mapped[str] = mapped_column(String(64))
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    file_bytes: Mapped[int] = mapped_column(Integer)
    checked: Mapped[bool] = mapped_column(Boolean)
    check: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    ip: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(300))


class SignatureAdoption(IdMixin, Base):
    __tablename__ = "signature_adoptions"
    __table_args__ = (
        *owner_checks(),
        Index("ix_signature_adoptions_user", "user_id", "created_at"),
        Index("ix_signature_adoptions_provider", "provider_id", "created_at"),
    )
    signature_id: Mapped[str] = mapped_column(ForeignKey("signatures.id"))
    practice_id: Mapped[str | None] = mapped_column(ForeignKey("practices.id"))
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    provider_id: Mapped[str | None] = mapped_column(ForeignKey("providers.id"))


class SigningEvent(IdMixin, Base):
    __tablename__ = "signing_events"
    __table_args__ = (
        one_of("event", SIGNING_EVENTS),
        one_of("signer_kind", SIGNER_KINDS),
        CheckConstraint(ONE_SIGNER, name="one_signer"),
        Index("ix_signing_events_note", "note_id", "signed_at"),
        Index("ix_signing_events_practice", "practice_id", "signed_at"),
    )
    practice_id: Mapped[str] = mapped_column(ForeignKey("practices.id"))
    note_id: Mapped[str | None] = mapped_column(ForeignKey("notes.id"))
    event: Mapped[str] = mapped_column(String(24))
    record_id: Mapped[str] = mapped_column(String(36))
    statement: Mapped[str] = mapped_column(Text)
    signer_kind: Mapped[str] = mapped_column(String(8))
    signer_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    signer_provider_id: Mapped[str | None] = mapped_column(ForeignKey("providers.id"))
    signer_name: Mapped[str] = mapped_column(String(SIGNER_NAME_LENGTH))
    signer_title: Mapped[str] = mapped_column(String(60))
    typed_name: Mapped[str] = mapped_column(String(SIGNER_NAME_LENGTH))
    signature_id: Mapped[str | None] = mapped_column(ForeignKey("signatures.id"))
    signature_sha256: Mapped[str | None] = mapped_column(String(64))
    document_sha256: Mapped[str | None] = mapped_column(String(64))
    content_sha256: Mapped[str] = mapped_column(String(64))
    signed_at: Mapped[datetime] = timestamp(nullable=False)
    ip: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(300))
    code: Mapped[str] = mapped_column(String(16), unique=True)
    schema_version: Mapped[int] = mapped_column(Integer)
    envelope: Mapped[str] = mapped_column(Text)
    envelope_sha256: Mapped[str] = mapped_column(String(64))
    seal: Mapped[str] = mapped_column(Text)
    seal_key_id: Mapped[str] = mapped_column(String(300))
    seal_algorithm: Mapped[str] = mapped_column(String(20))
