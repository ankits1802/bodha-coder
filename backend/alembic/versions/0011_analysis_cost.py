from decimal import Decimal

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None

DEFAULT_MODEL = "gemini-3.8-flash"
DEFAULT_INPUT_PRICE = Decimal("0.50")
DEFAULT_OUTPUT_PRICE = Decimal("3.00")
FINISHED_INDEX = "ix_analyses_finished_at"
BACKFILL = (
    "UPDATE analyses SET"
    " cost_microusd = round(coalesce(input_tokens, 0) * CAST(:input AS numeric)"
    " + coalesce(output_tokens, 0) * CAST(:output AS numeric)),"
    " price_snapshot = jsonb_build_object(model, jsonb_build_object("
    "'input', CAST(:input AS numeric), 'output', CAST(:output AS numeric)))"
    " WHERE model = :model AND status IN ('succeeded', 'superseded') AND cost_microusd IS NULL"
)


def backfill_statement() -> sa.TextClause:
    return sa.text(BACKFILL).bindparams(model=DEFAULT_MODEL, input=DEFAULT_INPUT_PRICE, output=DEFAULT_OUTPUT_PRICE)


def upgrade() -> None:
    op.add_column("analyses", sa.Column("cost_microusd", sa.BigInteger(), nullable=True))
    op.add_column("analyses", sa.Column("price_snapshot", JSONB(), nullable=True))
    op.create_index(op.f(FINISHED_INDEX), "analyses", ["finished_at"])
    op.execute(backfill_statement())


def downgrade() -> None:
    op.drop_index(op.f(FINISHED_INDEX), table_name="analyses")
    op.drop_column("analyses", "price_snapshot")
    op.drop_column("analyses", "cost_microusd")
