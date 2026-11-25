import sqlalchemy as sa
from alembic import op
from cryptography.fernet import Fernet

from app.core.config import get_settings

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

SEALED_PREFIX = "v1:"


def upgrade() -> None:
    op.alter_column("users", "mfa_secret", type_=sa.String(200), existing_type=sa.String(64), existing_nullable=True)
    op.add_column("users", sa.Column("mfa_last_step", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("google_sub", sa.String(255), nullable=True))
    op.create_unique_constraint(op.f("uq_users_google_sub"), "users", ["google_sub"])
    op.create_table(
        "recovery_codes",
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("code_hash", sa.String(64), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_recovery_codes_user_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_recovery_codes")),
    )
    op.create_index(op.f("ix_recovery_codes_user_id"), "recovery_codes", ["user_id"])
    op.create_table(
        "rate_events",
        sa.Column("bucket", sa.String(24), nullable=False),
        sa.Column("key_hash", sa.String(64), nullable=False),
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rate_events")),
    )
    op.create_index(op.f("ix_rate_events_key"), "rate_events", ["bucket", "key_hash", "created_at"])
    op.create_index(op.f("ix_rate_events_created_at"), "rate_events", ["created_at"])


def downgrade() -> None:
    op.drop_index(op.f("ix_rate_events_created_at"), table_name="rate_events")
    op.drop_index(op.f("ix_rate_events_key"), table_name="rate_events")
    op.drop_table("rate_events")
    op.drop_index(op.f("ix_recovery_codes_user_id"), table_name="recovery_codes")
    op.drop_table("recovery_codes")
    op.drop_constraint(op.f("uq_users_google_sub"), "users", type_="unique")
    op.drop_column("users", "google_sub")
    op.drop_column("users", "mfa_last_step")
    _open_sealed_secrets()
    op.alter_column("users", "mfa_secret", type_=sa.String(64), existing_type=sa.String(200), existing_nullable=True)


def _open_sealed_secrets() -> None:
    connection = op.get_bind()
    sealed = connection.execute(
        sa.text("SELECT id, mfa_secret FROM users WHERE mfa_secret LIKE :sealed"), {"sealed": SEALED_PREFIX + "%"}
    ).all()
    if not sealed:
        return
    key = get_settings().mfa_encryption_key
    if not key:
        raise RuntimeError("set MFA_ENCRYPTION_KEY to downgrade sealed two-step secrets")
    cipher = Fernet(key)
    for row in sealed:
        plain = cipher.decrypt(row.mfa_secret.removeprefix(SEALED_PREFIX).encode()).decode()
        connection.execute(
            sa.text("UPDATE users SET mfa_secret = :secret WHERE id = :id"), {"secret": plain, "id": row.id}
        )
