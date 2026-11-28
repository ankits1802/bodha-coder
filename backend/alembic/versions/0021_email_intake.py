import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None

RUNTIME_ROLE = "bodha_runtime"
NOW = sa.text("clock_timestamp()")
PURGE_FUNCTION = "bodha_purge_practice(text, integer)"
PURGE_ANCHOR = "    'DELETE FROM batches WHERE practice_id = $1',\n"
INTAKE_PURGE_STEPS = (
    "    'DELETE FROM intake_tests WHERE practice_id = $1',\n"
    "    'DELETE FROM intake_messages WHERE practice_id = $1',\n"
    "    'DELETE FROM intake_senders WHERE practice_id = $1',\n"
    "    'DELETE FROM intake_addresses WHERE practice_id = $1',\n"
)
SENDER_KINDS = ("address", "domain")
MESSAGE_OUTCOMES = ("accepted", "refused", "test")
REFUSAL_REASONS = (
    "unknown_address",
    "retired_address",
    "practice_closed",
    "failed_scan",
    "not_authenticated",
    "sender_not_allowed",
    "no_pdf",
    "too_many_files",
    "files_refused",
)
WRITTEN_ONCE = {
    "intake_addresses": ("id", "created_at", "practice_id", "local_part", "created_by", "retired_at", "retired_by"),
    "intake_senders": ("id", "created_at", "practice_id", "pattern", "kind", "added_by", "removed_at", "removed_by"),
    "intake_tests": (
        "id",
        "created_at",
        "practice_id",
        "address_id",
        "token_hash",
        "requested_by",
        "message_id",
        "arrived_at",
    ),
}
APPEND_ONLY = ("intake_messages",)
NEW_TABLES = ("intake_addresses", "intake_senders", "intake_messages", "intake_tests")
KEPT_DATA = "SELECT (SELECT count(*) FROM intake_addresses) + (SELECT count(*) FROM intake_messages)"


def _run(statement: str) -> None:
    op.get_bind().exec_driver_sql(statement)


def _allowed(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in values)})"


def _ledger(table: str) -> list[sa.SchemaItem]:
    return [
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.Column("practice_id", sa.String(36), nullable=table == "intake_messages"),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{table}")),
        _reference(table, "practice_id", "practices"),
    ]


def _reference(table: str, column: str, target: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint([column], [f"{target}.id"], name=op.f(f"fk_{table}_{column}_{target}"))


def _create_addresses() -> None:
    table = "intake_addresses"
    op.create_table(
        table,
        *_ledger(table),
        sa.Column("local_part", sa.String(32), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retired_by", sa.String(36), nullable=True),
        _reference(table, "created_by", "users"),
        _reference(table, "retired_by", "users"),
        sa.UniqueConstraint("local_part", name=op.f(f"uq_{table}_local_part")),
    )
    op.create_index(
        "uq_intake_addresses_current",
        table,
        ["practice_id"],
        unique=True,
        postgresql_where=sa.text("retired_at IS NULL"),
    )
    op.create_index("ix_intake_addresses_practice", table, ["practice_id", "created_at"])


def _create_senders() -> None:
    table = "intake_senders"
    op.create_table(
        table,
        *_ledger(table),
        sa.Column("pattern", sa.String(254), nullable=False),
        sa.Column("kind", sa.String(8), nullable=False),
        sa.Column("added_by", sa.String(36), nullable=True),
        sa.Column("removed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("removed_by", sa.String(36), nullable=True),
        _reference(table, "added_by", "users"),
        _reference(table, "removed_by", "users"),
        sa.CheckConstraint(_allowed("kind", SENDER_KINDS), name=op.f(f"ck_{table}_kind_allowed")),
    )
    op.create_index(
        "uq_intake_senders_current",
        table,
        ["practice_id", "pattern"],
        unique=True,
        postgresql_where=sa.text("removed_at IS NULL"),
    )


def _create_messages() -> None:
    table = "intake_messages"
    op.create_table(
        table,
        *_ledger(table),
        sa.Column("message_key", sa.String(128), nullable=False),
        sa.Column("address_id", sa.String(36), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sender", sa.String(254), nullable=True),
        sa.Column("outcome", sa.String(12), nullable=False),
        sa.Column("reason", sa.String(24), nullable=True),
        sa.Column("accepted_files", sa.Integer(), nullable=False),
        sa.Column("refused_files", sa.Integer(), nullable=False),
        sa.Column("files", JSONB(), nullable=False),
        sa.Column("verdicts", JSONB(), nullable=False),
        _reference(table, "address_id", "intake_addresses"),
        sa.UniqueConstraint(
            "message_key", "address_id", name=op.f(f"uq_{table}_message_key"), postgresql_nulls_not_distinct=True
        ),
        sa.CheckConstraint(_allowed("outcome", MESSAGE_OUTCOMES), name=op.f(f"ck_{table}_outcome_allowed")),
        sa.CheckConstraint(
            f"reason IS NULL OR {_allowed('reason', REFUSAL_REASONS)}", name=op.f(f"ck_{table}_reason_allowed")
        ),
        sa.CheckConstraint(
            "(outcome = 'refused') = (reason IS NOT NULL)", name=op.f(f"ck_{table}_refused_with_reason")
        ),
    )
    op.create_index("ix_intake_messages_practice", table, ["practice_id", "created_at"])


def _create_tests() -> None:
    table = "intake_tests"
    op.create_table(
        table,
        *_ledger(table),
        sa.Column("address_id", sa.String(36), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("requested_by", sa.String(36), nullable=True),
        sa.Column("message_id", sa.String(36), nullable=True),
        sa.Column("arrived_at", sa.DateTime(timezone=True), nullable=True),
        _reference(table, "address_id", "intake_addresses"),
        _reference(table, "requested_by", "users"),
        _reference(table, "message_id", "intake_messages"),
    )
    op.create_index("ix_intake_tests_address", table, ["address_id", "created_at"])


def _row_trigger(name: str, event: str, table: str, function: str) -> None:
    _run(f"CREATE TRIGGER {name} BEFORE {event} ON {table} FOR EACH ROW EXECUTE FUNCTION {function}")


def _protect() -> None:
    for table, columns in WRITTEN_ONCE.items():
        guarded = ", ".join(f"'{column}'" for column in columns)
        _row_trigger("bodha_no_delete", "DELETE", table, "bodha_reject_change()")
        _row_trigger("bodha_write_once", "UPDATE", table, f"bodha_write_once({guarded})")
    for table in APPEND_ONLY:
        _row_trigger("bodha_append_only", "UPDATE OR DELETE", table, "bodha_reject_change()")
    for table in NEW_TABLES:
        _row_trigger("bodha_stamp", "INSERT", table, "bodha_stamp('created_at')")
        _run(f"CREATE TRIGGER bodha_no_truncate BEFORE TRUNCATE ON {table} EXECUTE FUNCTION bodha_reject_change()")


def _unprotect() -> None:
    for table in WRITTEN_ONCE:
        _run(f"DROP TRIGGER bodha_no_delete ON {table}")
        _run(f"DROP TRIGGER bodha_write_once ON {table}")
    for table in APPEND_ONLY:
        _run(f"DROP TRIGGER bodha_append_only ON {table}")
    for table in NEW_TABLES:
        _run(f"DROP TRIGGER bodha_stamp ON {table}")
        _run(f"DROP TRIGGER bodha_no_truncate ON {table}")


def purge_with_intake(definition: str) -> str:
    if definition.count(PURGE_ANCHOR) != 1 or INTAKE_PURGE_STEPS in definition:
        raise RuntimeError(f"{PURGE_FUNCTION} no longer reads as this migration expects")
    return definition.replace(PURGE_ANCHOR, INTAKE_PURGE_STEPS + PURGE_ANCHOR, 1)


def purge_without_intake(definition: str) -> str:
    if definition.count(INTAKE_PURGE_STEPS) != 1:
        raise RuntimeError(f"{PURGE_FUNCTION} does not hold the email intake steps")
    return definition.replace(INTAKE_PURGE_STEPS, "", 1)


def _purge_definition() -> str:
    query = sa.text("SELECT pg_get_functiondef(CAST(:name AS regprocedure))")
    return op.get_bind().scalar(query, {"name": PURGE_FUNCTION})


def _runtime_role_exists() -> bool:
    found = op.get_bind().scalar(sa.text("SELECT 1 FROM pg_roles WHERE rolname = :name"), {"name": RUNTIME_ROLE})
    return bool(found)


def upgrade() -> None:
    _create_addresses()
    _create_senders()
    _create_messages()
    _create_tests()
    _protect()
    if _runtime_role_exists():
        _run(f"GRANT SELECT, INSERT, UPDATE ON {', '.join(WRITTEN_ONCE)} TO {RUNTIME_ROLE}")
        _run(f"GRANT SELECT, INSERT ON {', '.join(APPEND_ONLY)} TO {RUNTIME_ROLE}")
    _run(purge_with_intake(_purge_definition()))


def downgrade() -> None:
    if op.get_bind().scalar(sa.text(KEPT_DATA)):
        raise RuntimeError("email intake addresses or messages exist; the earlier schema cannot hold them")
    _run(purge_without_intake(_purge_definition()))
    _unprotect()
    for table in reversed(NEW_TABLES):
        op.drop_table(table)
