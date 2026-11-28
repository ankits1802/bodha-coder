import sqlalchemy as sa
from alembic import op

revision = "0028"
down_revision = "0027"
branch_labels = None
depends_on = None

CHOICES = {
    "theme": ("system", "light", "dark"),
    "text_size": ("default", "large", "larger"),
    "reduce_motion": ("system", "on", "off"),
}


def _allowed(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in values)})"


def upgrade() -> None:
    for column, values in CHOICES.items():
        op.add_column("users", sa.Column(column, sa.String(8), nullable=False, server_default=values[0]))
        op.create_check_constraint(op.f(f"ck_users_{column}_allowed"), "users", _allowed(column, values))


def downgrade() -> None:
    for column in reversed(CHOICES):
        op.drop_constraint(op.f(f"ck_users_{column}_allowed"), "users", type_="check")
        op.drop_column("users", column)
