import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

ACTOR_KIND = op.f("ck_access_log_actor_kind_allowed")


def upgrade() -> None:
    op.add_column("remittance_lines", sa.Column("appeal_plan_type", sa.String(24), nullable=True))
    op.drop_constraint(ACTOR_KIND, "access_log", type_="check")
    op.create_check_constraint(ACTOR_KIND, "access_log", "actor_kind IN ('user', 'provider', 'system')")


def downgrade() -> None:
    op.execute("UPDATE access_log SET actor_kind = 'user' WHERE actor_kind = 'system'")
    op.drop_constraint(ACTOR_KIND, "access_log", type_="check")
    op.create_check_constraint(ACTOR_KIND, "access_log", "actor_kind IN ('user', 'provider')")
    op.drop_column("remittance_lines", "appeal_plan_type")
