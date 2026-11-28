import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None

MEASURES = "practice_measures"
USAGE = "usage_events"
NEW_TABLES = (MEASURES, USAGE)
RUNTIME_ROLE = "bodha_runtime"
PURGE_FUNCTION = "bodha_purge_practice(text, integer)"
NOW = sa.text("clock_timestamp()")
TRIGGERS = ("bodha_append_only", "bodha_stamp", "bodha_no_truncate")
PRACTICE_ROLES = ("admin", "coder", "cdi", "compliance", "biller", "viewer")
KINDS = ("task", "stall")
TASKS = ("note_review", "queue", "upload", "billing_export")
OUTCOMES = ("completed", "left")
STEPS = ("summary", "note", "findings", "claim", "dialog", "history", "navigation", "queue", "upload", "billing")
COUNTS = ("key_inputs", "pointer_inputs", "key_decisions", "pointer_decisions")
PURGE_ANCHOR = "    'DELETE FROM mips_lists WHERE practice_id = $1',\n"
PURGE_STEPS = (
    "    'DELETE FROM usage_events WHERE practice_id = $1 OR user_id = ANY($2)',\n"
    "    'DELETE FROM practice_measures WHERE practice_id = $1',\n"
)
KEPT_DATA = "SELECT (SELECT count(*) FROM practice_measures) + (SELECT count(*) FROM usage_events)"


def purge_with_measures_and_usage(definition: str) -> str:
    if definition.count(PURGE_ANCHOR) != 1 or PURGE_STEPS in definition:
        raise RuntimeError(f"{PURGE_FUNCTION} no longer reads as this migration expects")
    return definition.replace(PURGE_ANCHOR, PURGE_STEPS + PURGE_ANCHOR, 1)


def purge_without_measures_and_usage(definition: str) -> str:
    if definition.count(PURGE_STEPS) != 1:
        raise RuntimeError(f"{PURGE_FUNCTION} does not hold the practice measure and usage steps")
    return definition.replace(PURGE_STEPS, "", 1)


def allowed(column: str, values: tuple[str, ...]) -> str:
    listed = ", ".join(f"'{value}'" for value in values)
    return f"{column} IN ({listed})"


def _run(statement: str) -> None:
    op.get_bind().exec_driver_sql(statement)


def _purge_definition() -> str:
    query = sa.text("SELECT pg_get_functiondef(CAST(:name AS regprocedure))")
    return op.get_bind().scalar(query, {"name": PURGE_FUNCTION})


def _runtime_role_exists() -> bool:
    found = op.get_bind().scalar(sa.text("SELECT 1 FROM pg_roles WHERE rolname = :name"), {"name": RUNTIME_ROLE})
    return bool(found)


def _ledger(table: str) -> list[sa.SchemaItem]:
    return [
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.Column("practice_id", sa.String(36), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{table}")),
        sa.ForeignKeyConstraint(["practice_id"], ["practices.id"], name=op.f(f"fk_{table}_practice_id_practices")),
    ]


def _check(table: str, name: str, condition: str) -> sa.CheckConstraint:
    return sa.CheckConstraint(condition, name=op.f(f"ck_{table}_{name}"))


def _create_measures() -> None:
    op.create_table(
        MEASURES,
        *_ledger(MEASURES),
        sa.Column("measure_key", sa.String(4), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("identifier", sa.String(20), nullable=True),
        sa.Column("in_scope", sa.String(600), nullable=False),
        sa.Column("out_of_scope", sa.String(600), nullable=True),
        sa.Column("to_meet", sa.String(1000), nullable=False),
        sa.Column("met_codes", JSONB(), nullable=False),
        sa.Column("not_met_codes", JSONB(), nullable=False),
        sa.Column("retired", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_by", sa.String(36), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name=op.f(f"fk_{MEASURES}_created_by_users")),
        sa.UniqueConstraint("practice_id", "measure_key", "version", name=op.f(f"uq_{MEASURES}_practice_id")),
        _check(MEASURES, "version_min", "version >= 1"),
        _check(MEASURES, "key_format", "measure_key ~ '^P[0-9]{3}$'"),
    )


def _usage_checks() -> list[sa.CheckConstraint]:
    counted = " AND ".join(f"{name} >= 0" for name in COUNTS)
    return [
        _check(USAGE, "role_allowed", allowed("role", PRACTICE_ROLES)),
        _check(USAGE, "kind_allowed", allowed("kind", KINDS)),
        _check(USAGE, "task_allowed", allowed("task", TASKS)),
        _check(USAGE, "step_allowed", allowed("step", STEPS)),
        _check(USAGE, "outcome_allowed", allowed("outcome", OUTCOMES)),
        _check(USAGE, "task_outcome", "(kind = 'task') = (outcome IS NOT NULL)"),
        _check(USAGE, "stall_step", "(kind = 'stall') = (step IS NOT NULL)"),
        _check(USAGE, "durations_min", "duration_ms >= 0 AND coalesce(first_decision_ms, 0) >= 0"),
        _check(USAGE, "counts_min", counted),
    ]


def _create_usage() -> None:
    op.create_table(
        USAGE,
        *_ledger(USAGE),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("client_event_id", sa.String(36), nullable=False),
        sa.Column("kind", sa.String(8), nullable=False),
        sa.Column("task", sa.String(16), nullable=False),
        sa.Column("step", sa.String(16), nullable=True),
        sa.Column("outcome", sa.String(12), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("first_decision_ms", sa.Integer(), nullable=True),
        *[sa.Column(name, sa.Integer(), nullable=False) for name in COUNTS],
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f(f"fk_{USAGE}_user_id_users")),
        sa.UniqueConstraint("user_id", "client_event_id", name=op.f(f"uq_{USAGE}_user_id")),
        *_usage_checks(),
    )
    op.create_index("ix_usage_events_practice", USAGE, ["practice_id", "created_at"])
    op.create_index("ix_usage_events_created", USAGE, ["created_at"])


def _protect(table: str) -> None:
    _run(
        f"CREATE TRIGGER bodha_append_only BEFORE UPDATE OR DELETE ON {table} "
        "FOR EACH ROW EXECUTE FUNCTION bodha_reject_change()"
    )
    _run(f"CREATE TRIGGER bodha_stamp BEFORE INSERT ON {table} FOR EACH ROW EXECUTE FUNCTION bodha_stamp('created_at')")
    _run(f"CREATE TRIGGER bodha_no_truncate BEFORE TRUNCATE ON {table} EXECUTE FUNCTION bodha_reject_change()")


def upgrade() -> None:
    _create_measures()
    _create_usage()
    for table in NEW_TABLES:
        _protect(table)
    if _runtime_role_exists():
        _run(f"GRANT SELECT, INSERT ON {', '.join(NEW_TABLES)} TO {RUNTIME_ROLE}")
    _run(purge_with_measures_and_usage(_purge_definition()))


def downgrade() -> None:
    if op.get_bind().scalar(sa.text(KEPT_DATA)):
        raise RuntimeError("practice measures or usage events exist; the earlier schema cannot hold them")
    _run(purge_without_measures_and_usage(_purge_definition()))
    for table in NEW_TABLES:
        for trigger in TRIGGERS:
            _run(f"DROP TRIGGER {trigger} ON {table}")
    op.drop_index("ix_usage_events_created", table_name=USAGE)
    op.drop_index("ix_usage_events_practice", table_name=USAGE)
    op.drop_table(USAGE)
    op.drop_table(MEASURES)
