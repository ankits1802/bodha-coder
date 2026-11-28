from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, ForeignKeyConstraint, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, LedgerMixin, one_of, timestamp

PRACTICE_MEMBER_ROLES = ("admin", "coder", "cdi", "compliance", "biller", "viewer")
MEMBERSHIP_STATUSES = ("invited", "active", "blocked")
AUTH_EVENT_KINDS = (
    "sign_in_failed",
    "signed_in",
    "password_set",
    "password_changed",
    "two_step_on",
    "two_step_off",
    "recovery_codes_replaced",
    "recovery_code_used",
    "signed_out",
    "session_revoked",
    "practice_switched",
    "sso_changed",
    "sso_tested",
)
AUTH_DETAIL_LENGTH = 200


class PracticeMembership(IdMixin, Base):
    __tablename__ = "practice_memberships"
    __table_args__ = (
        UniqueConstraint("user_id", "practice_id"),
        ForeignKeyConstraint(["user_id", "realm"], ["users.id", "users.realm"]),
        CheckConstraint("realm = 'practice'", name="realm_practice"),
        Index("ix_practice_memberships_practice_role", "practice_id", "role", "status"),
        one_of("role", PRACTICE_MEMBER_ROLES),
        one_of("status", MEMBERSHIP_STATUSES),
    )
    user_id: Mapped[str] = mapped_column(String(36))
    realm: Mapped[str] = mapped_column(String(16), server_default="practice")
    practice_id: Mapped[str] = mapped_column(ForeignKey("practices.id"))
    role: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16), default="invited")
    invited_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    ended_at: Mapped[datetime | None] = timestamp()


class RecoveryCode(IdMixin, Base):
    __tablename__ = "recovery_codes"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    code_hash: Mapped[str] = mapped_column(String(64))
    used_at: Mapped[datetime | None] = timestamp()


class AuthEvent(LedgerMixin, Base):
    __tablename__ = "auth_events"
    __table_args__ = (
        Index("ix_auth_events_user_time", "user_id", "created_at"),
        Index("ix_auth_events_practice_time", "practice_id", "created_at"),
        one_of("kind", AUTH_EVENT_KINDS),
    )
    kind: Mapped[str] = mapped_column(String(32))
    realm: Mapped[str | None] = mapped_column(String(16))
    user_id: Mapped[str | None] = mapped_column(String(36))
    practice_id: Mapped[str | None] = mapped_column(String(36))
    email_hash: Mapped[str | None] = mapped_column(String(64))
    detail: Mapped[str | None] = mapped_column(String(AUTH_DETAIL_LENGTH))
    ip: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(300))
