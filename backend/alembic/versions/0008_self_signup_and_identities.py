import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None

GOOGLE_SUB_UNIQUE = op.f("uq_users_google_sub")


def upgrade() -> None:
    op.add_column("practices", sa.Column("signup", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")))
    op.execute("""UPDATE practices SET signup = '{"source": "hq"}'::jsonb""")
    op.create_table(
        "user_identities",
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("provider", sa.String(16), nullable=False),
        sa.Column("subject", sa.String(255), nullable=False),
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_user_identities_user_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_identities")),
        sa.UniqueConstraint("provider", "subject", name=op.f("uq_user_identities_provider")),
        sa.UniqueConstraint("user_id", "provider", name=op.f("uq_user_identities_user_id")),
    )
    op.execute(
        "INSERT INTO user_identities (id, user_id, provider, subject, created_at) "
        "SELECT gen_random_uuid()::text, id, 'google', google_sub, now() FROM users WHERE google_sub IS NOT NULL"
    )
    op.drop_constraint(GOOGLE_SUB_UNIQUE, "users", type_="unique")
    op.drop_column("users", "google_sub")


def downgrade() -> None:
    op.add_column("users", sa.Column("google_sub", sa.String(255), nullable=True))
    op.create_unique_constraint(GOOGLE_SUB_UNIQUE, "users", ["google_sub"])
    op.execute(
        "UPDATE users SET google_sub = user_identities.subject FROM user_identities "
        "WHERE user_identities.user_id = users.id AND user_identities.provider = 'google'"
    )
    op.drop_table("user_identities")
    op.drop_column("practices", "signup")
