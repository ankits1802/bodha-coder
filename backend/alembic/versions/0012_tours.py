import sqlalchemy as sa
from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "person_tours",
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("tour", sa.String(16), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("skipped_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("tour IN ('hq', 'practice')", name=op.f("ck_person_tours_tour_allowed")),
        sa.CheckConstraint("version >= 1", name=op.f("ck_person_tours_version_min")),
        sa.CheckConstraint("(completed_at IS NULL) <> (skipped_at IS NULL)", name=op.f("ck_person_tours_one_outcome")),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_person_tours_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("user_id", "tour", "version", name=op.f("pk_person_tours")),
    )


def downgrade() -> None:
    op.drop_table("person_tours")
