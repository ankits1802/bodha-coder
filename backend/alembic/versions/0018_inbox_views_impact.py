import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0018"
down_revision = "0014"
branch_labels = None
depends_on = None

INBOX_KINDS = (
    "provider_answered",
    "level_disagreed",
    "request_expired",
    "mentioned",
    "training_assigned",
    "payment_failed",
    "plan_ending",
    "compliance_returned",
)
RECIPIENT_INDEX = "ix_inbox_items_recipient"


def _owned(table: str) -> list[sa.SchemaItem]:
    return [
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("practice_id", sa.String(36), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{table}")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f(f"fk_{table}_user_id_users")),
        sa.ForeignKeyConstraint(["practice_id"], ["practices.id"], name=op.f(f"fk_{table}_practice_id_practices")),
    ]


def upgrade() -> None:
    allowed = ", ".join(f"'{kind}'" for kind in INBOX_KINDS)
    op.create_table(
        "inbox_items",
        *_owned("inbox_items"),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("note_id", sa.String(36), nullable=True),
        sa.Column("actor_id", sa.String(36), nullable=True),
        sa.Column("actor_name", sa.String(120), nullable=False),
        sa.Column("payload", JSONB(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(f"kind IN ({allowed})", name=op.f("ck_inbox_items_kind_allowed")),
    )
    op.create_index(RECIPIENT_INDEX, "inbox_items", ["user_id", "practice_id", "created_at"])
    op.create_table(
        "queue_views",
        *_owned("queue_views"),
        sa.Column("name", sa.String(60), nullable=False),
        sa.Column("filters", JSONB(), nullable=False),
        sa.UniqueConstraint("user_id", "practice_id", "name", name=op.f("uq_queue_views_user_id")),
    )
    op.add_column("notes", sa.Column("impact_cents", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("notes", "impact_cents")
    op.drop_table("queue_views")
    op.drop_index(RECIPIENT_INDEX, table_name="inbox_items")
    op.drop_table("inbox_items")
