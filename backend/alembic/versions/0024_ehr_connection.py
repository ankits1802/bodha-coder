import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0024"
down_revision = "0021"
branch_labels = None
depends_on = None

RUNTIME_ROLE = "bodha_runtime"
NOW = sa.text("clock_timestamp()")
PURGE_FUNCTION = "bodha_purge_practice(text, integer)"
PURGE_ANCHOR = "    'DELETE FROM notes WHERE practice_id = $1',\n"
EHR_PURGE_STEPS = (
    "    'DELETE FROM ehr_documents WHERE practice_id = $1',\n"
    "    'DELETE FROM ehr_pull_runs WHERE practice_id = $1',\n"
    "    'DELETE FROM ehr_connections WHERE practice_id = $1',\n"
    "    'DELETE FROM ehr_keys WHERE practice_id = $1',\n"
)
BATCH_SOURCE_CHECK = "ck_batches_source_allowed"
SOURCES_BEFORE = ("upload", "intake")
SOURCES_AFTER = ("upload", "intake", "fhir")
KEY_ALGORITHMS = ("RS384", "ES384")
CHANGES = ("saved", "paused", "resumed")
PULL_OUTCOMES = ("succeeded", "partial", "failed")
PULL_REASONS = (
    "no_key",
    "unsafe_address",
    "unreachable",
    "timeout",
    "too_large",
    "rate_limited",
    "redirected",
    "no_configuration",
    "token_refused",
    "server_refused",
    "server_error",
    "bad_response",
    "foreign_link",
)
RUN_COUNTS = ("pages", "accepted", "duplicates", "refused", "skipped")
DOCUMENT_OUTCOMES = ("accepted", "duplicate", "refused")
DOCUMENT_REASONS = (
    "not_final",
    "no_attachment",
    "unsupported_format",
    "too_large",
    "attachment_unavailable",
    "attachment_mismatch",
    "file_refused",
    "no_service_date",
    "future_service_date",
    "no_provider",
    "no_place",
    "foreign_reference",
    "upload_refused",
)
WRITTEN_ONCE = {
    "ehr_keys": (
        "id",
        "created_at",
        "practice_id",
        "key_set",
        "algorithm",
        "public_jwk",
        "private_key",
        "created_by",
        "retired_at",
        "retired_by",
    ),
    "ehr_pull_runs": (
        "id",
        "created_at",
        "practice_id",
        "connection_id",
        "since",
        "finished_at",
        "outcome",
        "reason",
        "cursor",
        "pages",
        "accepted",
        "duplicates",
        "refused",
        "skipped",
    ),
}
APPEND_ONLY = ("ehr_connections", "ehr_documents")
NEW_TABLES = ("ehr_keys", "ehr_connections", "ehr_pull_runs", "ehr_documents")
KEPT_DATA = (
    "SELECT (SELECT count(*) FROM ehr_keys) + (SELECT count(*) FROM ehr_connections)"
    " + (SELECT count(*) FROM batches WHERE source = 'fhir')"
)


def _run(statement: str) -> None:
    op.get_bind().exec_driver_sql(statement)


def _allowed(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in values)})"


def _ledger(table: str) -> list[sa.SchemaItem]:
    return [
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.Column("practice_id", sa.String(36), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{table}")),
        _reference(table, "practice_id", "practices"),
    ]


def _reference(table: str, column: str, target: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint([column], [f"{target}.id"], name=op.f(f"fk_{table}_{column}_{target}"))


def _create_keys() -> None:
    table = "ehr_keys"
    op.create_table(
        table,
        *_ledger(table),
        sa.Column("key_set", sa.String(32), nullable=False),
        sa.Column("algorithm", sa.String(8), nullable=False),
        sa.Column("public_jwk", JSONB(), nullable=False),
        sa.Column("private_key", sa.Text(), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retired_by", sa.String(36), nullable=True),
        _reference(table, "created_by", "users"),
        _reference(table, "retired_by", "users"),
        sa.CheckConstraint(_allowed("algorithm", KEY_ALGORITHMS), name=op.f(f"ck_{table}_algorithm_allowed")),
    )
    op.create_index(
        "uq_ehr_keys_current", table, ["practice_id"], unique=True, postgresql_where=sa.text("retired_at IS NULL")
    )
    op.create_index("ix_ehr_keys_key_set", table, ["key_set"])


def _create_connections() -> None:
    table = "ehr_connections"
    op.create_table(
        table,
        *_ledger(table),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("base_url", sa.String(500), nullable=False),
        sa.Column("token_endpoint", sa.String(500), nullable=False),
        sa.Column("client_id", sa.String(200), nullable=False),
        sa.Column("scopes", sa.String(1000), nullable=False),
        sa.Column("note_types", JSONB(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("paused", sa.Boolean(), nullable=False),
        sa.Column("change", sa.String(12), nullable=False),
        sa.Column("changed_by", sa.String(36), nullable=True),
        _reference(table, "changed_by", "users"),
        sa.UniqueConstraint("practice_id", "revision", name=op.f(f"uq_{table}_practice_id")),
        sa.CheckConstraint(_allowed("change", CHANGES), name=op.f(f"ck_{table}_change_allowed")),
    )


def _create_runs() -> None:
    table = "ehr_pull_runs"
    op.create_table(
        table,
        *_ledger(table),
        sa.Column("connection_id", sa.String(36), nullable=False),
        sa.Column("since", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("outcome", sa.String(12), nullable=True),
        sa.Column("reason", sa.String(24), nullable=True),
        sa.Column("cursor", sa.DateTime(timezone=True), nullable=True),
        *(sa.Column(name, sa.Integer(), nullable=True) for name in RUN_COUNTS),
        _reference(table, "connection_id", "ehr_connections"),
        sa.CheckConstraint(
            f"outcome IS NULL OR {_allowed('outcome', PULL_OUTCOMES)}", name=op.f(f"ck_{table}_outcome_allowed")
        ),
        sa.CheckConstraint(
            f"reason IS NULL OR {_allowed('reason', PULL_REASONS)}", name=op.f(f"ck_{table}_reason_allowed")
        ),
        sa.CheckConstraint("(outcome = 'failed') = (reason IS NOT NULL)", name=op.f(f"ck_{table}_failed_with_reason")),
    )
    op.create_index("ix_ehr_pull_runs_practice", table, ["practice_id", "created_at"])


def _create_documents() -> None:
    table = "ehr_documents"
    op.create_table(
        table,
        *_ledger(table),
        sa.Column("run_id", sa.String(36), nullable=False),
        sa.Column("document_id", sa.String(64), nullable=False),
        sa.Column("document_version", sa.String(64), nullable=False),
        sa.Column("encounter_id", sa.String(64), nullable=True),
        sa.Column("practitioner_id", sa.String(64), nullable=True),
        sa.Column("outcome", sa.String(12), nullable=False),
        sa.Column("reason", sa.String(24), nullable=True),
        sa.Column("note_id", sa.String(36), nullable=True),
        sa.Column("file_sha256", sa.String(64), nullable=True),
        sa.Column("file_bytes", sa.Integer(), nullable=True),
        _reference(table, "run_id", "ehr_pull_runs"),
        _reference(table, "note_id", "notes"),
        sa.CheckConstraint(_allowed("outcome", DOCUMENT_OUTCOMES), name=op.f(f"ck_{table}_outcome_allowed")),
        sa.CheckConstraint(
            f"reason IS NULL OR {_allowed('reason', DOCUMENT_REASONS)}", name=op.f(f"ck_{table}_reason_allowed")
        ),
        sa.CheckConstraint(
            "(outcome = 'refused') = (reason IS NOT NULL)", name=op.f(f"ck_{table}_refused_with_reason")
        ),
    )
    op.create_index("ix_ehr_documents_practice", table, ["practice_id", "created_at"])
    op.create_index("ix_ehr_documents_resource", table, ["practice_id", "document_id"])
    op.create_index("ix_ehr_documents_run", table, ["run_id"])


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


def _batch_sources(values: tuple[str, ...]) -> None:
    op.drop_constraint(op.f(BATCH_SOURCE_CHECK), "batches", type_="check")
    op.create_check_constraint(op.f(BATCH_SOURCE_CHECK), "batches", _allowed("source", values))


def purge_with_ehr(definition: str) -> str:
    if definition.count(PURGE_ANCHOR) != 1 or EHR_PURGE_STEPS in definition:
        raise RuntimeError(f"{PURGE_FUNCTION} no longer reads as this migration expects")
    return definition.replace(PURGE_ANCHOR, EHR_PURGE_STEPS + PURGE_ANCHOR, 1)


def purge_without_ehr(definition: str) -> str:
    if definition.count(EHR_PURGE_STEPS) != 1:
        raise RuntimeError(f"{PURGE_FUNCTION} does not hold the EHR connection steps")
    return definition.replace(EHR_PURGE_STEPS, "", 1)


def _purge_definition() -> str:
    query = sa.text("SELECT pg_get_functiondef(CAST(:name AS regprocedure))")
    return op.get_bind().scalar(query, {"name": PURGE_FUNCTION})


def _runtime_role_exists() -> bool:
    found = op.get_bind().scalar(sa.text("SELECT 1 FROM pg_roles WHERE rolname = :name"), {"name": RUNTIME_ROLE})
    return bool(found)


def upgrade() -> None:
    _create_keys()
    _create_connections()
    _create_runs()
    _create_documents()
    _protect()
    _batch_sources(SOURCES_AFTER)
    if _runtime_role_exists():
        _run(f"GRANT SELECT, INSERT, UPDATE ON {', '.join(WRITTEN_ONCE)} TO {RUNTIME_ROLE}")
        _run(f"GRANT SELECT, INSERT ON {', '.join(APPEND_ONLY)} TO {RUNTIME_ROLE}")
    _run(purge_with_ehr(_purge_definition()))


def downgrade() -> None:
    if op.get_bind().scalar(sa.text(KEPT_DATA)):
        raise RuntimeError("EHR keys, connections or batches from an EHR exist; the earlier schema cannot hold them")
    _run(purge_without_ehr(_purge_definition()))
    _batch_sources(SOURCES_BEFORE)
    _unprotect()
    for table in reversed(NEW_TABLES):
        op.drop_table(table)
