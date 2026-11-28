from alembic import op

revision = "0027"
down_revision = "0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE practices SET idle_minutes = 10080")


def downgrade() -> None:
    op.execute("UPDATE practices SET idle_minutes = 15 WHERE idle_minutes NOT IN (5, 10, 15, 30)")
