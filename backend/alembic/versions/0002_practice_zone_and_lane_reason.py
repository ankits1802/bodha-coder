import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

LANE_REASONS = (
    "flagged",
    "levels_too_high",
    "audit_risk",
    "waiting_on_provider",
    "code_changes",
    "questions",
    "matches",
)


def upgrade() -> None:
    op.add_column("practices", sa.Column("time_zone", sa.String(64), nullable=False, server_default="America/Chicago"))
    op.add_column("notes", sa.Column("lane_reason", sa.String(24), nullable=True))
    allowed = ", ".join(f"'{item}'" for item in LANE_REASONS)
    op.create_check_constraint(
        op.f("ck_notes_lane_reason_allowed"), "notes", f"lane_reason IS NULL OR lane_reason IN ({allowed})"
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_notes_lane_reason_allowed"), "notes", type_="check")
    op.drop_column("notes", "lane_reason")
    op.drop_column("practices", "time_zone")
