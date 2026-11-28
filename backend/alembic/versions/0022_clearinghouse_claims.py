import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None

RUNTIME_ROLE = "bodha_runtime"
NOW = sa.text("clock_timestamp()")
PURGE_FUNCTION = "bodha_purge_practice(text, integer)"
PURGE_ANCHOR = "    'DELETE FROM claim_export_items WHERE practice_id = $1',\n"
CLAIM_PURGE_STEPS = (
    "    'DELETE FROM claim_acks WHERE practice_id = $1',\n"
    "    'DELETE FROM claim_ack_files WHERE practice_id = $1',\n"
    "    'DELETE FROM claim_deliveries WHERE practice_id = $1',\n"
    "    'DELETE FROM claim_submission_items WHERE practice_id = $1',\n"
    "    'DELETE FROM claim_submissions WHERE practice_id = $1',\n"
    "    'DELETE FROM claim_details WHERE practice_id = $1',\n"
    "    'DELETE FROM clearinghouse_connections WHERE practice_id = $1',\n"
)
INBOX_KINDS = (
    "provider_answered",
    "level_disagreed",
    "request_expired",
    "mentioned",
    "training_assigned",
    "payment_failed",
    "plan_ending",
    "compliance_returned",
    "join_requested",
)
REJECTION_KIND = "claim_rejected"
ID_QUALIFIERS = ("01", "14", "20", "27", "28", "29", "30", "33", "ZZ")
WRITTEN_ONCE_TABLE = "clearinghouse_connections"
APPEND_ONLY = (
    "claim_details",
    "claim_submissions",
    "claim_submission_items",
    "claim_deliveries",
    "claim_ack_files",
    "claim_acks",
)
NEW_TABLES = (WRITTEN_ONCE_TABLE, *APPEND_ONLY)
SFTP_COMPLETE = (
    "transport <> 'sftp' OR (host IS NOT NULL AND port IS NOT NULL AND username IS NOT NULL AND auth_kind IS NOT NULL"
    " AND secret IS NOT NULL AND host_key_sha256 IS NOT NULL AND outbound_folder IS NOT NULL"
    " AND inbound_folder IS NOT NULL)"
)
KEPT_DATA = (
    "SELECT (SELECT count(*) FROM clearinghouse_connections) + (SELECT count(*) FROM claim_details)"
    " + (SELECT count(*) FROM claim_ack_files) + (SELECT count(*) FROM inbox_items WHERE kind = 'claim_rejected')"
)


def _run(statement: str) -> None:
    op.get_bind().exec_driver_sql(statement)


def allowed(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in values)})"


def _check(table: str, name: str, condition: str) -> sa.CheckConstraint:
    return sa.CheckConstraint(condition, name=op.f(f"ck_{table}_{name}"))


def _reference(table: str, column: str, target: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint([column], [f"{target}.id"], name=op.f(f"fk_{table}_{column}_{target}"))


def _ledger(table: str) -> list[sa.SchemaItem]:
    return [
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.Column("practice_id", sa.String(36), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{table}")),
        _reference(table, "practice_id", "practices"),
    ]


def _text(name: str, length: int, *, nullable: bool = False) -> sa.Column:
    return sa.Column(name, sa.String(length), nullable=nullable)


def _connection_checks(table: str) -> list[sa.CheckConstraint]:
    return [
        _check(table, "transport_allowed", allowed("transport", ("sftp", "portal"))),
        _check(table, "usage_allowed", allowed("usage", ("test", "production"))),
        _check(table, "sender_qualifier_allowed", allowed("sender_qualifier", ID_QUALIFIERS)),
        _check(table, "receiver_qualifier_allowed", allowed("receiver_qualifier", ID_QUALIFIERS)),
        _check(table, "auth_kind_allowed", "auth_kind IS NULL OR auth_kind IN ('password', 'key')"),
        _check(table, "port_range", "port IS NULL OR port BETWEEN 1 AND 65535"),
        _check(table, "sftp_complete", SFTP_COMPLETE),
    ]


def connection_columns() -> list[sa.Column]:
    return [
        _text("name", 80),
        _text("transport", 8),
        _text("usage", 12),
        _text("sender_qualifier", 2),
        _text("sender_id", 15),
        _text("receiver_qualifier", 2),
        _text("receiver_id", 15),
        _text("receiver_name", 60),
        _text("host", 253, nullable=True),
        sa.Column("port", sa.Integer(), nullable=True),
        _text("username", 128, nullable=True),
        _text("auth_kind", 8, nullable=True),
        sa.Column("secret", sa.Text(), nullable=True),
        _text("host_key_sha256", 80, nullable=True),
        _text("outbound_folder", 255, nullable=True),
        _text("inbound_folder", 255, nullable=True),
        _text("created_by", 36, nullable=True),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        _text("retired_by", 36, nullable=True),
    ]


def written_once_columns() -> tuple[str, ...]:
    return ("id", "created_at", "practice_id", *(column.name for column in connection_columns()))


def _create_connections() -> None:
    table = WRITTEN_ONCE_TABLE
    op.create_table(
        table,
        *_ledger(table),
        *connection_columns(),
        _reference(table, "created_by", "users"),
        _reference(table, "retired_by", "users"),
        *_connection_checks(table),
    )
    op.create_index(
        "uq_clearinghouse_connections_current",
        table,
        ["practice_id"],
        unique=True,
        postgresql_where=sa.text("retired_at IS NULL"),
    )
    op.create_index("ix_clearinghouse_connections_practice", table, ["practice_id", "created_at"])


def _create_details() -> None:
    table = "claim_details"
    op.create_table(
        table,
        *_ledger(table),
        _text("note_id", 36),
        sa.Column("revision", sa.Integer(), nullable=False),
        _text("patient_last", 60),
        _text("patient_first", 35),
        sa.Column("patient_birth_date", sa.Date(), nullable=False),
        _text("patient_sex", 1),
        _text("street", 55),
        _text("street_2", 55, nullable=True),
        _text("city", 30),
        _text("state", 2),
        _text("zip_code", 9),
        _text("relationship", 2),
        _text("member_id", 80),
        _text("group_number", 50, nullable=True),
        _text("subscriber_last", 60, nullable=True),
        _text("subscriber_first", 35, nullable=True),
        _text("confirmed_by", 36),
        _text("confirmer_name", 120),
        _text("confirmer_role", 16),
        _reference(table, "note_id", "notes"),
        _reference(table, "confirmed_by", "users"),
        sa.UniqueConstraint("note_id", "revision", name=op.f(f"uq_{table}_note_id")),
        _check(table, "relationship_allowed", allowed("relationship", ("18", "01", "19", "G8"))),
        _check(table, "patient_sex_allowed", allowed("patient_sex", ("F", "M", "U"))),
        _check(
            table,
            "subscriber_named",
            "relationship = '18' OR (subscriber_last IS NOT NULL AND subscriber_first IS NOT NULL)",
        ),
    )
    op.create_index("ix_claim_details_practice", table, ["practice_id", "created_at"])


def _actor_columns(table: str) -> list[sa.SchemaItem]:
    return [
        _text("actor_id", 36),
        _text("actor_name", 120),
        _reference(table, "actor_id", "users"),
    ]


def _create_submissions() -> None:
    table = "claim_submissions"
    op.create_table(
        table,
        *_ledger(table),
        _text("connection_id", 36),
        _text("delivery", 8),
        _text("usage", 12),
        _text("sender_qualifier", 2),
        _text("sender_id", 15),
        _text("receiver_id", 15),
        sa.Column("control_number", sa.Integer(), nullable=False),
        _text("batch_ref", 32),
        _text("file_key", 300),
        _text("file_sha256", 64),
        sa.Column("file_bytes", sa.Integer(), nullable=False),
        sa.Column("claims_count", sa.Integer(), nullable=False),
        sa.Column("total_cents", sa.BigInteger(), nullable=False),
        *_actor_columns(table),
        _text("actor_role", 16),
        _text("ip", 64, nullable=True),
        _text("user_agent", 300, nullable=True),
        _reference(table, "connection_id", "clearinghouse_connections"),
        sa.UniqueConstraint(
            "sender_qualifier", "sender_id", "control_number", name=op.f(f"uq_{table}_sender_qualifier")
        ),
        sa.UniqueConstraint("batch_ref", name=op.f(f"uq_{table}_batch_ref")),
        _check(table, "delivery_allowed", allowed("delivery", ("sftp", "download"))),
        _check(table, "usage_allowed", allowed("usage", ("test", "production"))),
        _check(table, "control_number_range", "control_number BETWEEN 1 AND 999999999"),
    )
    op.create_index("ix_claim_submissions_practice", table, ["practice_id", "created_at"])


def _create_items() -> None:
    table = "claim_submission_items"
    op.create_table(
        table,
        *_ledger(table),
        _text("submission_id", 36),
        _text("note_id", 36),
        _text("approved_claim_id", 36),
        sa.Column("snapshot_revision", sa.Integer(), nullable=False),
        _text("claim_detail_id", 36),
        _text("payer_key", 36),
        _text("claim_ref", 20),
        sa.Column("charge_cents", sa.BigInteger(), nullable=False),
        sa.Column("lines_count", sa.Integer(), nullable=False),
        _reference(table, "submission_id", "claim_submissions"),
        _reference(table, "note_id", "notes"),
        _reference(table, "approved_claim_id", "approved_claims"),
        _reference(table, "claim_detail_id", "claim_details"),
        sa.UniqueConstraint("submission_id", "note_id", name=op.f(f"uq_{table}_submission_id")),
        sa.UniqueConstraint("claim_ref", "submission_id", name=op.f(f"uq_{table}_claim_ref")),
    )
    op.create_index("ix_claim_submission_items_note", table, ["note_id", "created_at"])
    op.create_index("ix_claim_submission_items_practice", table, ["practice_id", "claim_ref"])


def _create_deliveries() -> None:
    table = "claim_deliveries"
    op.create_table(
        table,
        *_ledger(table),
        _text("submission_id", 36),
        _text("outcome", 12),
        _text("remote_name", 120, nullable=True),
        _text("error", 300, nullable=True),
        *_actor_columns(table),
        _reference(table, "submission_id", "claim_submissions"),
        _check(table, "outcome_allowed", allowed("outcome", ("delivered", "failed", "downloaded"))),
        _check(table, "failed_with_error", "(outcome = 'failed') = (error IS NOT NULL)"),
    )
    op.create_index("ix_claim_deliveries_submission", table, ["submission_id", "created_at"])


def _create_ack_files() -> None:
    table = "claim_ack_files"
    op.create_table(
        table,
        *_ledger(table),
        _text("connection_id", 36, nullable=True),
        _text("source", 8),
        _text("kind", 12),
        _text("remote_name_sha256", 64, nullable=True),
        _text("file_key", 300),
        _text("file_sha256", 64),
        sa.Column("file_bytes", sa.Integer(), nullable=False),
        _text("error", 300, nullable=True),
        _text("uploaded_by", 36, nullable=True),
        _reference(table, "connection_id", "clearinghouse_connections"),
        _reference(table, "uploaded_by", "users"),
        _check(table, "source_allowed", allowed("source", ("sftp", "upload"))),
        _check(table, "kind_allowed", allowed("kind", ("999", "277CA", "other", "unreadable", "duplicate"))),
        _check(table, "uploaded_by_a_person", "(source = 'upload') = (uploaded_by IS NOT NULL)"),
    )
    op.create_index("ix_claim_ack_files_practice", table, ["practice_id", "created_at"])
    op.create_index("ix_claim_ack_files_sha256", table, ["practice_id", "file_sha256"])
    op.create_index("ix_claim_ack_files_remote", table, ["practice_id", "remote_name_sha256"])


def _create_acks() -> None:
    table = "claim_acks"
    op.create_table(
        table,
        *_ledger(table),
        _text("file_id", 36),
        _text("kind", 6),
        _text("level", 6),
        _text("outcome", 10),
        _text("submission_id", 36, nullable=True),
        _text("item_id", 36, nullable=True),
        _text("note_id", 36, nullable=True),
        _text("claim_ref", 20, nullable=True),
        _text("payer_claim_number", 50, nullable=True),
        sa.Column("reasons", JSONB(), nullable=False),
        _reference(table, "file_id", "claim_ack_files"),
        _reference(table, "submission_id", "claim_submissions"),
        _reference(table, "item_id", "claim_submission_items"),
        _reference(table, "note_id", "notes"),
        _check(table, "kind_allowed", allowed("kind", ("999", "277CA"))),
        _check(table, "level_allowed", allowed("level", ("file", "claim"))),
        _check(table, "outcome_allowed", allowed("outcome", ("accepted", "rejected", "pending"))),
        _check(table, "claim_level_item", "level = 'file' OR item_id IS NOT NULL OR submission_id IS NULL"),
    )
    op.create_index("ix_claim_acks_submission", table, ["submission_id", "created_at"])
    op.create_index("ix_claim_acks_note", table, ["note_id", "created_at"])
    op.create_index("ix_claim_acks_file", table, ["file_id"])


def _inbox_kinds(kinds: tuple[str, ...]) -> None:
    op.drop_constraint(op.f("ck_inbox_items_kind_allowed"), "inbox_items", type_="check")
    op.create_check_constraint(op.f("ck_inbox_items_kind_allowed"), "inbox_items", allowed("kind", kinds))


def _row_trigger(name: str, event: str, table: str, function: str) -> None:
    _run(f"CREATE TRIGGER {name} BEFORE {event} ON {table} FOR EACH ROW EXECUTE FUNCTION {function}")


def _protect() -> None:
    guarded = ", ".join(f"'{column}'" for column in written_once_columns())
    _row_trigger("bodha_no_delete", "DELETE", WRITTEN_ONCE_TABLE, "bodha_reject_change()")
    _row_trigger("bodha_write_once", "UPDATE", WRITTEN_ONCE_TABLE, f"bodha_write_once({guarded})")
    for table in APPEND_ONLY:
        _row_trigger("bodha_append_only", "UPDATE OR DELETE", table, "bodha_reject_change()")
    for table in NEW_TABLES:
        _row_trigger("bodha_stamp", "INSERT", table, "bodha_stamp('created_at')")
        _run(f"CREATE TRIGGER bodha_no_truncate BEFORE TRUNCATE ON {table} EXECUTE FUNCTION bodha_reject_change()")


def _unprotect() -> None:
    _run(f"DROP TRIGGER bodha_no_delete ON {WRITTEN_ONCE_TABLE}")
    _run(f"DROP TRIGGER bodha_write_once ON {WRITTEN_ONCE_TABLE}")
    for table in APPEND_ONLY:
        _run(f"DROP TRIGGER bodha_append_only ON {table}")
    for table in NEW_TABLES:
        _run(f"DROP TRIGGER bodha_stamp ON {table}")
        _run(f"DROP TRIGGER bodha_no_truncate ON {table}")


def purge_with_claims(definition: str) -> str:
    if definition.count(PURGE_ANCHOR) != 1 or CLAIM_PURGE_STEPS in definition:
        raise RuntimeError(f"{PURGE_FUNCTION} no longer reads as this migration expects")
    return definition.replace(PURGE_ANCHOR, CLAIM_PURGE_STEPS + PURGE_ANCHOR, 1)


def purge_without_claims(definition: str) -> str:
    if definition.count(CLAIM_PURGE_STEPS) != 1:
        raise RuntimeError(f"{PURGE_FUNCTION} does not hold the clearinghouse claim steps")
    return definition.replace(CLAIM_PURGE_STEPS, "", 1)


def _purge_definition() -> str:
    query = sa.text("SELECT pg_get_functiondef(CAST(:name AS regprocedure))")
    return op.get_bind().scalar(query, {"name": PURGE_FUNCTION})


def _runtime_role_exists() -> bool:
    found = op.get_bind().scalar(sa.text("SELECT 1 FROM pg_roles WHERE rolname = :name"), {"name": RUNTIME_ROLE})
    return bool(found)


def upgrade() -> None:
    _create_connections()
    _create_details()
    _create_submissions()
    _create_items()
    _create_deliveries()
    _create_ack_files()
    _create_acks()
    _protect()
    _inbox_kinds((*INBOX_KINDS, REJECTION_KIND))
    if _runtime_role_exists():
        _run(f"GRANT SELECT, INSERT, UPDATE ON {WRITTEN_ONCE_TABLE} TO {RUNTIME_ROLE}")
        _run(f"GRANT SELECT, INSERT ON {', '.join(APPEND_ONLY)} TO {RUNTIME_ROLE}")
    _run(purge_with_claims(_purge_definition()))


def downgrade() -> None:
    if op.get_bind().scalar(sa.text(KEPT_DATA)):
        raise RuntimeError("clearinghouse connections, claim details or acknowledgments exist; 0021 cannot hold them")
    _run(purge_without_claims(_purge_definition()))
    _inbox_kinds(INBOX_KINDS)
    _unprotect()
    for table in reversed(NEW_TABLES):
        op.drop_table(table)
