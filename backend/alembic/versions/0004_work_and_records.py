import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("practices", sa.Column("access_log_years", sa.Integer(), nullable=False, server_default="6"))
    op.create_check_constraint(op.f("ck_practices_access_log_years_min"), "practices", "access_log_years >= 6")
    op.add_column("users", sa.Column("notify_digest", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("providers", sa.Column("details", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")))
    op.add_column("notes", sa.Column("assigned_to", sa.String(36), nullable=True))
    op.create_foreign_key(op.f("fk_notes_assigned_to_users"), "notes", "users", ["assigned_to"], ["id"])
    op.create_index(op.f("ix_notes_assigned_to"), "notes", ["assigned_to"])


def downgrade() -> None:
    op.drop_index(op.f("ix_notes_assigned_to"), table_name="notes")
    op.drop_constraint(op.f("fk_notes_assigned_to_users"), "notes", type_="foreignkey")
    op.drop_column("notes", "assigned_to")
    op.drop_column("providers", "details")
    op.drop_column("users", "notify_digest")
    op.drop_constraint(op.f("ck_practices_access_log_years_min"), "practices", type_="check")
    op.drop_column("practices", "access_log_years")
