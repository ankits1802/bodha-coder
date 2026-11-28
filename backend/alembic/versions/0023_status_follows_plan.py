from alembic import op

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE practices SET status = 'active' WHERE status = 'trial' AND plan <> 'trial'")


def downgrade() -> None:
    pass
