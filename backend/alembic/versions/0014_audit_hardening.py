import base64
import hashlib
import hmac
import os
import secrets
from pathlib import Path

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0014"
down_revision = "0010"
branch_labels = None
depends_on = None

FUNCTIONS = Path(__file__).with_name("0014_audit_hardening.sql")
RUNTIME_ROLE = "bodha_runtime"
PASSWORD_VARIABLE = "RUNTIME_DATABASE_PASSWORD"
SCRAM_ITERATIONS = 4096
NOW = sa.text("clock_timestamp()")
OLD_ACCESS_LOG_YEARS, ACCESS_LOG_YEARS = 6, 7
OLD_NOTE_STATUSES = "'queued', 'reading', 'ready', 'failed', 'approved', 'exported'"
OLD_PRACTICE_STATUSES = "'trial', 'active', 'ended', 'blocked'"
APPEND_ONLY = (
    "decisions",
    "code_sets",
    "suggestions",
    "note_texts",
    "access_log",
    "activity",
    "billing_events",
    "remittance_lines",
    "batches",
    "analysis_failures",
    "note_changes",
    "audit_chain_anchors",
)
CHAINED = ("access_log", "activity")
STAMPED = {
    **{table: "created_at" for table in APPEND_ONLY if table not in (*CHAINED, "billing_events")},
    "analyses": "created_at",
    "billing_events": "received_at",
}
WRITE_ONCE = {
    "analyses": (
        "id",
        "note_id",
        "revision",
        "reason",
        "created_at",
        "report",
        "response_key",
        "prompt_key",
        "prompt_sha256",
        "document_key",
        "app_version",
        "generation",
        "model",
        "prompt_version",
        "input_tokens",
        "output_tokens",
        "finished_at",
    ),
    "remittances": (
        "id",
        "created_at",
        "practice_id",
        "file_key",
        "file_name",
        "payer",
        "paid_on",
        "uploaded_by",
        "file_sha256",
    ),
    "addendum_requests": (
        "id",
        "created_at",
        "practice_id",
        "note_id",
        "analysis_id",
        "provider_id",
        "questions",
        "sent_by",
        "answers",
        "addendum_text",
        "answered_at",
    ),
}
NO_DELETE = ("notes", "practices", "users", "providers", "subscriptions", "audit_runs", "audit_samples", "eval_runs")
RETAINED = (*APPEND_ONLY, *WRITE_ONCE, *NO_DELETE)
DELETABLE = ("recovery_codes", "user_tokens", "sessions", "rate_events", "user_identities", "mips_lists", "eval_cases")
FUNCTION_SIGNATURES = (
    "bodha_purge_practice(text, integer)",
    "bodha_purge_access_log(text, timestamptz)",
    "bodha_practice_closure()",
    "bodha_verify_audit_log()",
    "bodha_verify_chain(text)",
    "bodha_link_problem(bigint, text, bigint, text, text, text)",
    "bodha_link_activity()",
    "bodha_link_access_log()",
    "bodha_chain_start(text)",
    "bodha_activity_content(activity)",
    "bodha_access_log_content(access_log)",
    "bodha_utc_text(timestamptz)",
    "bodha_link_hash(text, text)",
    "bodha_stamp()",
    "bodha_write_once()",
    "bodha_reject_change()",
    "bodha_maintenance(oid)",
)
RUNTIME_FUNCTIONS = FUNCTION_SIGNATURES[:2]


def upgrade() -> None:
    _add_columns()
    _create_tables()
    _change_constraints()
    for table, column in {**STAMPED, **{table: "created_at" for table in CHAINED}}.items():
        op.alter_column(table, column, server_default=NOW)
    for statement in FUNCTIONS.read_text(encoding="utf-8").split("\n;\n"):
        if statement.strip():
            _run(statement)
    _seal_chains()
    _create_triggers()
    _runtime_role()


def _run(statement: str) -> None:
    op.get_bind().exec_driver_sql(statement)


def _literal(text: str) -> str:
    return "'" + text.replace("'", "''") + "'"


def _add_columns() -> None:
    op.add_column("notes", sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("notes", sa.Column("voided_by", sa.String(36), nullable=True))
    op.add_column("notes", sa.Column("void_reason", sa.Text(), nullable=True))
    op.add_column("notes", sa.Column("status_before_void", sa.String(16), nullable=True))
    op.create_foreign_key(op.f("fk_notes_voided_by_users"), "notes", "users", ["voided_by"], ["id"])
    op.add_column("practices", sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("practices", sa.Column("closed_by", sa.String(36), nullable=True))
    op.add_column("practices", sa.Column("purged_at", sa.DateTime(timezone=True), nullable=True))
    for column in ("prompt_key", "document_key"):
        op.add_column("analyses", sa.Column(column, sa.String(300), nullable=True))
    op.add_column("analyses", sa.Column("prompt_sha256", sa.String(64), nullable=True))
    op.add_column("analyses", sa.Column("app_version", sa.String(64), nullable=True))
    op.add_column("analyses", sa.Column("generation", JSONB(), nullable=True))
    op.add_column("activity", sa.Column("changes", JSONB(), nullable=True))
    for table in CHAINED:
        op.add_column(table, sa.Column("chain_seq", sa.BigInteger(), nullable=True))
        op.add_column(table, sa.Column("prev_hash", sa.String(64), nullable=True))
        op.add_column(table, sa.Column("row_hash", sa.String(64), nullable=True))
    op.create_index("ix_access_log_practice_note", "access_log", ["practice_id", "note_id"])


def _ledger_columns() -> list[sa.Column]:
    return [
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
    ]


def _create_tables() -> None:
    op.create_table(
        "audit_chain_anchors",
        *_ledger_columns(),
        sa.Column("chain", sa.String(80), nullable=False),
        sa.Column("through_seq", sa.BigInteger(), nullable=False),
        sa.Column("through_hash", sa.String(64), nullable=False),
        sa.Column("rows_removed", sa.Integer(), nullable=False),
        sa.UniqueConstraint("chain", "through_seq", name=op.f("uq_audit_chain_anchors_chain")),
    )
    op.create_table(
        "note_changes",
        *_ledger_columns(),
        sa.Column(
            "note_id",
            sa.String(36),
            sa.ForeignKey("notes.id", name=op.f("fk_note_changes_note_id_notes")),
            nullable=False,
        ),
        sa.Column("actor_id", sa.String(36), sa.ForeignKey("users.id", name=op.f("fk_note_changes_actor_id_users"))),
        sa.Column("field", sa.String(16), nullable=False),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "field IN ('status', 'flag', 'payer', 'assignee', 'visit_type')", name=op.f("ck_note_changes_field_allowed")
        ),
    )
    op.create_index(op.f("ix_note_changes_note_id"), "note_changes", ["note_id"])
    _create_analysis_failures()


def _create_analysis_failures() -> None:
    op.create_table(
        "analysis_failures",
        *_ledger_columns(),
        sa.Column(
            "analysis_id",
            sa.String(36),
            sa.ForeignKey("analyses.id", name=op.f("fk_analysis_failures_analysis_id_analyses")),
            nullable=False,
        ),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("error", sa.String(300), nullable=False),
        sa.Column("retried", sa.Boolean(), nullable=False),
    )
    op.create_index(op.f("ix_analysis_failures_analysis_id"), "analysis_failures", ["analysis_id"])


def _change_constraints() -> None:
    op.drop_constraint(op.f("ck_notes_status_allowed"), "notes", type_="check")
    op.create_check_constraint(op.f("ck_notes_status_allowed"), "notes", f"status IN ({OLD_NOTE_STATUSES}, 'voided')")
    op.drop_constraint(op.f("uq_notes_practice_id"), "notes", type_="unique")
    op.create_index(
        "uq_notes_practice_file",
        "notes",
        ["practice_id", "file_sha256"],
        unique=True,
        postgresql_where=sa.text("status <> 'voided'"),
    )
    op.drop_constraint(op.f("ck_practices_status_allowed"), "practices", type_="check")
    op.create_check_constraint(
        op.f("ck_practices_status_allowed"), "practices", f"status IN ({OLD_PRACTICE_STATUSES}, 'closed', 'purged')"
    )
    op.create_check_constraint(
        op.f("ck_practices_closed_when_closed_at"),
        "practices",
        "(status IN ('closed', 'purged')) = (closed_at IS NOT NULL)",
    )
    years = ACCESS_LOG_YEARS
    op.execute(f"UPDATE practices SET access_log_years = {years} WHERE access_log_years < {years}")
    op.drop_constraint(op.f("ck_practices_access_log_years_min"), "practices", type_="check")
    op.create_check_constraint(
        op.f("ck_practices_access_log_years_min"), "practices", f"access_log_years >= {ACCESS_LOG_YEARS}"
    )
    op.alter_column("practices", "access_log_years", server_default=str(ACCESS_LOG_YEARS))


def _seal_chains() -> None:
    _run("SELECT bodha_backfill_chains()")
    _run("DROP FUNCTION bodha_backfill_chains()")
    for table in CHAINED:
        for column in ("chain_seq", "prev_hash", "row_hash"):
            op.alter_column(table, column, nullable=False)
    op.create_unique_constraint(op.f("uq_access_log_practice_id"), "access_log", ["practice_id", "chain_seq"])
    op.create_unique_constraint(op.f("uq_activity_chain_seq"), "activity", ["chain_seq"])


def _row_trigger(name: str, event: str, table: str, function: str) -> None:
    _run(f"CREATE TRIGGER {name} BEFORE {event} ON {table} FOR EACH ROW EXECUTE FUNCTION {function}")


def _create_triggers() -> None:
    for table in APPEND_ONLY:
        _row_trigger("bodha_append_only", "UPDATE OR DELETE", table, "bodha_reject_change()")
    for table in (*WRITE_ONCE, *NO_DELETE):
        _row_trigger("bodha_no_delete", "DELETE", table, "bodha_reject_change()")
    for table, columns in WRITE_ONCE.items():
        _row_trigger("bodha_write_once", "UPDATE", table, f"bodha_write_once({', '.join(map(_literal, columns))})")
    for table, column in STAMPED.items():
        _row_trigger("bodha_stamp", "INSERT", table, f"bodha_stamp({_literal(column)})")
    for table in CHAINED:
        _row_trigger("bodha_chain", "INSERT", table, f"bodha_link_{table}()")
    _row_trigger("bodha_closure", "INSERT OR UPDATE", "practices", "bodha_practice_closure()")
    for table in RETAINED:
        _run(f"CREATE TRIGGER bodha_no_truncate BEFORE TRUNCATE ON {table} EXECUTE FUNCTION bodha_reject_change()")
    for signature in RUNTIME_FUNCTIONS:
        _run(f"REVOKE ALL ON FUNCTION {signature} FROM PUBLIC")


def _role_exists() -> bool:
    return bool(op.get_bind().scalar(sa.text("SELECT 1 FROM pg_roles WHERE rolname = :name"), {"name": RUNTIME_ROLE}))


def _runtime_role() -> None:
    password = os.environ.get(PASSWORD_VARIABLE, "")
    if password:
        verb = "ALTER" if _role_exists() else "CREATE"
        limits = "NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS"
        _run(f"{verb} ROLE {RUNTIME_ROLE} LOGIN {limits} PASSWORD '{_scram_verifier(password)}'")
    if _role_exists():
        _grant_runtime()


def _scram_verifier(password: str) -> str:
    salt = secrets.token_bytes(16)
    salted = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, SCRAM_ITERATIONS)
    stored = hashlib.sha256(hmac.new(salted, b"Client Key", hashlib.sha256).digest()).digest()
    server = hmac.new(salted, b"Server Key", hashlib.sha256).digest()
    encoded = [base64.b64encode(part).decode("ascii") for part in (salt, stored, server)]
    return f"SCRAM-SHA-256${SCRAM_ITERATIONS}:{encoded[0]}${encoded[1]}:{encoded[2]}"


def _grant_runtime() -> None:
    bind = op.get_bind()
    database = bind.scalar(sa.text("SELECT quote_ident(current_database())"))
    tables = bind.scalars(sa.text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")).all()
    _run(f"GRANT CONNECT ON DATABASE {database} TO {RUNTIME_ROLE}")
    _run(f"GRANT USAGE ON SCHEMA public TO {RUNTIME_ROLE}")
    _run(f"GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA public TO {RUNTIME_ROLE}")
    _run(f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {RUNTIME_ROLE}")
    _run(f"REVOKE ALL ON alembic_version FROM {RUNTIME_ROLE}")
    for table in sorted(set(tables) - set(APPEND_ONLY) - {"alembic_version"}):
        _run(f"GRANT UPDATE ON {table} TO {RUNTIME_ROLE}")
    for table in DELETABLE:
        _run(f"GRANT DELETE ON {table} TO {RUNTIME_ROLE}")
    _run(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT ON TABLES TO {RUNTIME_ROLE}")
    for signature in RUNTIME_FUNCTIONS:
        _run(f"GRANT EXECUTE ON FUNCTION {signature} TO {RUNTIME_ROLE}")


def downgrade() -> None:
    if _role_exists():
        _run(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM {RUNTIME_ROLE}")
        _run(f"REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {RUNTIME_ROLE}")
        _run(f"REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM {RUNTIME_ROLE}")
    for table in RETAINED + ("practices",):
        for name in ("bodha_append_only", "bodha_no_delete", "bodha_write_once", "bodha_stamp", "bodha_chain"):
            _run(f"DROP TRIGGER IF EXISTS {name} ON {table}")
        _run(f"DROP TRIGGER IF EXISTS bodha_no_truncate ON {table}")
    _run("DROP TRIGGER IF EXISTS bodha_closure ON practices")
    for signature in FUNCTION_SIGNATURES:
        _run(f"DROP FUNCTION IF EXISTS {signature}")
    _restore_rows()
    for table, column in {**STAMPED, **{table: "created_at" for table in CHAINED}}.items():
        op.alter_column(table, column, server_default=None)
    _drop_columns()


def _restore_rows() -> None:
    clash = op.get_bind().scalar(
        sa.text(
            "SELECT count(*) FROM notes AS voided JOIN notes AS live ON live.practice_id = voided.practice_id"
            " AND live.file_sha256 = voided.file_sha256 AND live.id <> voided.id"
            " WHERE voided.status = 'voided' AND live.status <> 'voided'"
        )
    )
    if clash:
        raise RuntimeError(f"{clash} voided notes hold a PDF that another note now holds; restore or settle them first")
    op.execute("UPDATE notes SET status = coalesce(status_before_void, 'failed') WHERE status = 'voided'")
    op.execute("UPDATE practices SET status = 'ended', closed_at = NULL WHERE status IN ('closed', 'purged')")


def _drop_columns() -> None:
    op.drop_constraint(op.f("ck_practices_access_log_years_min"), "practices", type_="check")
    op.create_check_constraint(
        op.f("ck_practices_access_log_years_min"), "practices", f"access_log_years >= {OLD_ACCESS_LOG_YEARS}"
    )
    op.alter_column("practices", "access_log_years", server_default=str(OLD_ACCESS_LOG_YEARS))
    op.drop_constraint(op.f("ck_practices_closed_when_closed_at"), "practices", type_="check")
    op.drop_constraint(op.f("ck_practices_status_allowed"), "practices", type_="check")
    op.create_check_constraint(op.f("ck_practices_status_allowed"), "practices", f"status IN ({OLD_PRACTICE_STATUSES})")
    op.drop_index("uq_notes_practice_file", table_name="notes")
    op.create_unique_constraint(op.f("uq_notes_practice_id"), "notes", ["practice_id", "file_sha256"])
    op.drop_constraint(op.f("ck_notes_status_allowed"), "notes", type_="check")
    op.create_check_constraint(op.f("ck_notes_status_allowed"), "notes", f"status IN ({OLD_NOTE_STATUSES})")
    for table in ("analysis_failures", "note_changes", "audit_chain_anchors"):
        op.drop_table(table)
    op.drop_constraint(op.f("uq_activity_chain_seq"), "activity", type_="unique")
    op.drop_constraint(op.f("uq_access_log_practice_id"), "access_log", type_="unique")
    op.drop_index("ix_access_log_practice_note", table_name="access_log")
    for table in CHAINED:
        for column in ("chain_seq", "prev_hash", "row_hash"):
            op.drop_column(table, column)
    op.drop_column("activity", "changes")
    for column in ("generation", "app_version", "prompt_sha256", "document_key", "prompt_key"):
        op.drop_column("analyses", column)
    for column in ("purged_at", "closed_by", "closed_at"):
        op.drop_column("practices", column)
    op.drop_constraint(op.f("fk_notes_voided_by_users"), "notes", type_="foreignkey")
    for column in ("status_before_void", "void_reason", "voided_by", "voided_at"):
        op.drop_column("notes", column)
