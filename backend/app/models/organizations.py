from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, ForeignKey, ForeignKeyConstraint, Index, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.accounts import PRACTICE_MEMBER_ROLES
from app.models.base import Base, LedgerMixin, one_of, timestamp

ORGANIZATION_STATUSES = ("active", "closed", "purged")
ORGANIZATION_CLOSED_STATUSES = ("closed", "purged")
ORGANIZATION_ROLES = ("admin",)
DOMAIN_LENGTH = 253
JOIN_MODES = ("off", "request", "auto")
VERIFICATION_METHODS = ("dns", "email")
JOIN_REQUEST_STATUSES = ("pending", "approved", "declined", "joined")


class Organization(LedgerMixin, Base):
    __tablename__ = "organizations"
    __table_args__ = (
        one_of("status", ORGANIZATION_STATUSES),
        CheckConstraint(
            f"(status IN ({', '.join(repr(item) for item in ORGANIZATION_CLOSED_STATUSES)})) = (closed_at IS NOT NULL)",
            name="closed_when_closed_at",
        ),
    )
    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(16), default="active")
    plan: Mapped[str] = mapped_column(String(16), default="trial")
    renews_on: Mapped[date | None] = mapped_column(Date)
    closed_at: Mapped[datetime | None] = timestamp()
    closed_by: Mapped[str | None] = mapped_column(String(36))
    purged_at: Mapped[datetime | None] = timestamp()


class OrganizationMembership(LedgerMixin, Base):
    __tablename__ = "organization_memberships"
    __table_args__ = (
        UniqueConstraint("user_id", "organization_id"),
        ForeignKeyConstraint(["user_id", "realm"], ["users.id", "users.realm"]),
        CheckConstraint("realm = 'practice'", name="realm_practice"),
        Index("ix_organization_memberships_organization", "organization_id", "role"),
        one_of("role", ORGANIZATION_ROLES),
    )
    user_id: Mapped[str] = mapped_column(String(36))
    realm: Mapped[str] = mapped_column(String(16), server_default="practice")
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"))
    role: Mapped[str] = mapped_column(String(16), default="admin")
    added_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    ended_at: Mapped[datetime | None] = timestamp()


class DomainClaim(LedgerMixin, Base):
    __tablename__ = "domain_claims"
    __table_args__ = (
        Index(
            "uq_domain_claims_verified_domain",
            "domain",
            unique=True,
            postgresql_where=text("verified_at IS NOT NULL AND released_at IS NULL"),
        ),
        Index("ix_domain_claims_practice", "practice_id"),
        Index("ix_domain_claims_organization", "organization_id"),
        one_of("join_mode", JOIN_MODES),
        one_of("join_role", PRACTICE_MEMBER_ROLES),
        CheckConstraint(
            f"verified_via IS NULL OR verified_via IN ({', '.join(repr(item) for item in VERIFICATION_METHODS)})",
            name="verified_via_allowed",
        ),
        CheckConstraint("(verified_at IS NULL) = (verified_via IS NULL)", name="verified_with_method"),
    )
    domain: Mapped[str] = mapped_column(String(DOMAIN_LENGTH))
    practice_id: Mapped[str] = mapped_column(ForeignKey("practices.id"))
    organization_id: Mapped[str | None] = mapped_column(ForeignKey("organizations.id"))
    claimed_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    token: Mapped[str] = mapped_column(String(64))
    email_token_hash: Mapped[str | None] = mapped_column(String(64), unique=True)
    email_sent_to: Mapped[str | None] = mapped_column(String(320))
    email_expires_at: Mapped[datetime | None] = timestamp()
    verified_at: Mapped[datetime | None] = timestamp()
    verified_via: Mapped[str | None] = mapped_column(String(8))
    join_mode: Mapped[str] = mapped_column(String(8), default="off")
    join_role: Mapped[str] = mapped_column(String(16), default="viewer")
    released_at: Mapped[datetime | None] = timestamp()
    released_by: Mapped[str | None] = mapped_column(String(36))


class DomainJoinRequest(LedgerMixin, Base):
    __tablename__ = "domain_join_requests"
    __table_args__ = (
        Index(
            "uq_domain_join_requests_pending",
            "practice_id",
            "email",
            unique=True,
            postgresql_where=text("status = 'pending'"),
        ),
        Index("ix_domain_join_requests_practice", "practice_id", "status", "created_at"),
        one_of("status", JOIN_REQUEST_STATUSES),
        CheckConstraint(
            f"role IS NULL OR role IN ({', '.join(repr(item) for item in PRACTICE_MEMBER_ROLES)})",
            name="role_allowed",
        ),
    )
    claim_id: Mapped[str] = mapped_column(ForeignKey("domain_claims.id"))
    practice_id: Mapped[str] = mapped_column(ForeignKey("practices.id"))
    email: Mapped[str] = mapped_column(String(254))
    name: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(12), default="pending")
    role: Mapped[str | None] = mapped_column(String(16))
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    decided_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    decided_at: Mapped[datetime | None] = timestamp()
