import sqlalchemy as sa
from alembic import op

revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None

TABLE = "providers"
COLUMN = "payer"


def upgrade() -> None:
    op.add_column(TABLE, sa.Column(COLUMN, sa.String(64), nullable=True))


def downgrade() -> None:
    op.drop_column(TABLE, COLUMN)
