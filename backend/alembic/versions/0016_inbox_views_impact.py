from pathlib import Path

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0016"
down_revision = "0015"
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
RUNTIME_ROLE = "bodha_runtime"
PREVIOUS_FUNCTIONS = Path(__file__).with_name("0015_audit_hardening.sql")
PURGE_HEAD = "CREATE FUNCTION bodha_purge_practice("
SESSIONS_STEP = "    'DELETE FROM sessions WHERE practice_id = $1 OR user_id = ANY($2)',\n"
WORK_ITEM_STEPS = (
    "    'DELETE FROM inbox_items WHERE practice_id = $1 OR user_id = ANY($2)',\n"
    "    'DELETE FROM queue_views WHERE practice_id = $1 OR user_id = ANY($2)',\n"
)


def previous_purge() -> str:
    statements = PREVIOUS_FUNCTIONS.read_text(encoding="utf-8").split("\n;\n")
    found = [statement.strip() for statement in statements if statement.strip().startswith(PURGE_HEAD)]
    if len(found) != 1:
        raise RuntimeError("0015 must define bodha_purge_practice exactly once")
    return found[0].replace(PURGE_HEAD, "CREATE OR REPLACE FUNCTION bodha_purge_practice(", 1)


def purge_with_work_items() -> str:
    previous = previous_purge()
    if previous.count(SESSIONS_STEP) != 1:
        raise RuntimeError("bodha_purge_practice no longer has the sessions step to add the work item steps before")
    return previous.replace(SESSIONS_STEP, WORK_ITEM_STEPS + SESSIONS_STEP, 1)


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


def _run(statement: str) -> None:
    op.get_bind().exec_driver_sql(statement)


def _role_exists() -> bool:
    return bool(op.get_bind().scalar(sa.text("SELECT 1 FROM pg_roles WHERE rolname = :name"), {"name": RUNTIME_ROLE}))


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
    _run(purge_with_work_items())
    if _role_exists():
        _run(f"GRANT SELECT, INSERT, UPDATE ON inbox_items, queue_views TO {RUNTIME_ROLE}")
        _run(f"GRANT DELETE ON queue_views TO {RUNTIME_ROLE}")
        _run(f"GRANT UPDATE (impact_cents) ON notes TO {RUNTIME_ROLE}")


def downgrade() -> None:
    _run(previous_purge())
    op.drop_column("notes", "impact_cents")
    op.drop_table("queue_views")
    op.drop_index(RECIPIENT_INDEX, table_name="inbox_items")
    op.drop_table("inbox_items")
