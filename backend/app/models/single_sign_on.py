from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.accounts import PRACTICE_MEMBER_ROLES
from app.models.base import Base, LedgerMixin, timestamp

SSO_NEW_PERSON_ROLES = tuple(role for role in PRACTICE_MEMBER_ROLES if role != "admin")
SSO_ENTITY_ID_LENGTH = 1024
SSO_URL_LENGTH = 2048
SSO_ATTRIBUTE_LENGTH = 255
SSO_AUTHOR_LENGTH = 120
ASSERTION_KEY_LENGTH = 64


class SsoConnection(LedgerMixin, Base):
    __tablename__ = "sso_connections"
    __table_args__ = (
        CheckConstraint("(practice_id IS NULL) <> (organization_id IS NULL)", name="one_owner"),
        Index("uq_sso_connections_practice", "practice_id", unique=True, postgresql_where=text("removed_at IS NULL")),
        Index(
            "uq_sso_connections_organization",
            "organization_id",
            unique=True,
            postgresql_where=text("removed_at IS NULL"),
        ),
    )
    practice_id: Mapped[str | None] = mapped_column(ForeignKey("practices.id"))
    organization_id: Mapped[str | None] = mapped_column(ForeignKey("organizations.id"))
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    removed_at: Mapped[datetime | None] = timestamp()
    removed_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))


class SsoVersion(LedgerMixin, Base):
    __tablename__ = "sso_versions"
    __table_args__ = (
        UniqueConstraint("connection_id", "version"),
        CheckConstraint("version >= 1", name="version_min"),
        CheckConstraint(
            f"new_person_role IS NULL OR new_person_role IN ({', '.join(repr(role) for role in SSO_NEW_PERSON_ROLES)})",
            name="new_person_role_allowed",
        ),
        CheckConstraint("NOT create_people OR new_person_role IS NOT NULL", name="role_for_new_people"),
    )
    connection_id: Mapped[str] = mapped_column(ForeignKey("sso_connections.id"))
    version: Mapped[int] = mapped_column(Integer)
    idp_entity_id: Mapped[str] = mapped_column(String(SSO_ENTITY_ID_LENGTH))
    sso_url: Mapped[str] = mapped_column(String(SSO_URL_LENGTH))
    certificates: Mapped[list[str]] = mapped_column(JSONB)
    metadata_url: Mapped[str | None] = mapped_column(String(SSO_URL_LENGTH))
    claim_ids: Mapped[list[str]] = mapped_column(JSONB)
    email_attribute: Mapped[str | None] = mapped_column(String(SSO_ATTRIBUTE_LENGTH))
    name_attribute: Mapped[str | None] = mapped_column(String(SSO_ATTRIBUTE_LENGTH))
    create_people: Mapped[bool] = mapped_column(Boolean)
    new_person_role: Mapped[str | None] = mapped_column(String(16))
    required: Mapped[bool] = mapped_column(Boolean)
    break_glass: Mapped[list[str]] = mapped_column(JSONB)
    mfa_context: Mapped[str | None] = mapped_column(String(SSO_ATTRIBUTE_LENGTH))
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    author_name: Mapped[str] = mapped_column(String(SSO_AUTHOR_LENGTH))


class SsoAssertion(LedgerMixin, Base):
    __tablename__ = "sso_assertions"
    __table_args__ = (Index("ix_sso_assertions_connection", "connection_id", "created_at"),)
    connection_id: Mapped[str] = mapped_column(ForeignKey("sso_connections.id"))
    assertion_key: Mapped[str] = mapped_column(String(ASSERTION_KEY_LENGTH), unique=True)
    expires_at: Mapped[datetime] = timestamp(nullable=False)
