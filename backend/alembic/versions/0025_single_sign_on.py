import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0025"
down_revision = "0024"
branch_labels = None
depends_on = None

RUNTIME_ROLE = "bodha_runtime"
NOW = sa.text("clock_timestamp()")
PRACTICE_PURGE = "bodha_purge_practice(text, integer)"
ORGANIZATION_PURGE = "bodha_purge_organization(text, integer)"
PRACTICE_ANCHOR = "    'DELETE FROM domain_join_requests WHERE practice_id = $1',\n"
ORGANIZATION_ANCHOR = (
    "    'DELETE FROM domain_join_requests WHERE claim_id IN "
    "(SELECT id FROM domain_claims WHERE organization_id = $1)',\n"
)
NEW_PERSON_ROLES = ("coder", "cdi", "compliance", "biller", "viewer")
EARLIER_KINDS = (
    "sign_in_failed",
    "signed_in",
    "password_set",
    "password_changed",
    "two_step_on",
    "two_step_off",
    "recovery_codes_replaced",
    "recovery_code_used",
    "signed_out",
    "session_revoked",
    "practice_switched",
)
AUTH_EVENT_KINDS = (*EARLIER_KINDS, "sso_changed", "sso_tested")
CONNECTIONS = "sso_connections"
APPEND_ONLY = ("sso_versions", "sso_assertions")
NEW_TABLES = (CONNECTIONS, *APPEND_ONLY)
CONNECTION_COLUMNS = ("id", "created_at", "practice_id", "organization_id", "created_by", "removed_at", "removed_by")
KEPT_DATA = "SELECT (SELECT count(*) FROM sso_connections) + (SELECT count(*) FROM auth_events WHERE kind LIKE 'sso_%')"


def owner_steps(column: str) -> str:
    owned = f"(SELECT id FROM sso_connections WHERE {column} = $1)"
    return (
        f"    'DELETE FROM sso_assertions WHERE connection_id IN {owned}',\n"
        f"    'DELETE FROM sso_versions WHERE connection_id IN {owned}',\n"
        f"    'DELETE FROM sso_connections WHERE {column} = $1',\n"
    )


PRACTICE_STEPS = owner_steps("practice_id")
ORGANIZATION_STEPS = owner_steps("organization_id")


def with_steps(definition: str, anchor: str, steps: str, name: str) -> str:
    if definition.count(anchor) != 1 or steps in definition:
        raise RuntimeError(f"{name} no longer reads as this migration expects")
    return definition.replace(anchor, steps + anchor, 1)


def without_steps(definition: str, steps: str, name: str) -> str:
    if definition.count(steps) != 1:
        raise RuntimeError(f"{name} does not hold the single sign-on steps")
    return definition.replace(steps, "", 1)


def allowed(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in values)})"


def _run(statement: str) -> None:
    op.get_bind().exec_driver_sql(statement)


def _reference(table: str, column: str, target: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint([column], [f"{target}.id"], name=op.f(f"fk_{table}_{column}_{target}"))


def _ledger(table: str) -> list[sa.SchemaItem]:
    return [
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{table}")),
    ]


def _create_connections() -> None:
    table = CONNECTIONS
    op.create_table(
        table,
        *_ledger(table),
        sa.Column("practice_id", sa.String(36), nullable=True),
        sa.Column("organization_id", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=False),
        sa.Column("removed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("removed_by", sa.String(36), nullable=True),
        _reference(table, "practice_id", "practices"),
        _reference(table, "organization_id", "organizations"),
        _reference(table, "created_by", "users"),
        _reference(table, "removed_by", "users"),
        sa.CheckConstraint("(practice_id IS NULL) <> (organization_id IS NULL)", name=op.f(f"ck_{table}_one_owner")),
    )
    for owner in ("practice", "organization"):
        where = sa.text("removed_at IS NULL")
        op.create_index(f"uq_{table}_{owner}", table, [f"{owner}_id"], unique=True, postgresql_where=where)


def _version_columns() -> list[sa.Column]:
    return [
        sa.Column("connection_id", sa.String(36), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("idp_entity_id", sa.String(1024), nullable=False),
        sa.Column("sso_url", sa.String(2048), nullable=False),
        sa.Column("certificates", JSONB(), nullable=False),
        sa.Column("metadata_url", sa.String(2048), nullable=True),
        sa.Column("claim_ids", JSONB(), nullable=False),
        sa.Column("email_attribute", sa.String(255), nullable=True),
        sa.Column("name_attribute", sa.String(255), nullable=True),
        sa.Column("create_people", sa.Boolean(), nullable=False),
        sa.Column("new_person_role", sa.String(16), nullable=True),
        sa.Column("required", sa.Boolean(), nullable=False),
        sa.Column("break_glass", JSONB(), nullable=False),
        sa.Column("mfa_context", sa.String(255), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("author_name", sa.String(120), nullable=False),
    ]


def _create_versions() -> None:
    table = "sso_versions"
    op.create_table(
        table,
        *_ledger(table),
        *_version_columns(),
        _reference(table, "connection_id", CONNECTIONS),
        _reference(table, "created_by", "users"),
        sa.UniqueConstraint("connection_id", "version", name=op.f(f"uq_{table}_connection_id")),
        sa.CheckConstraint("version >= 1", name=op.f(f"ck_{table}_version_min")),
        sa.CheckConstraint(
            f"new_person_role IS NULL OR {allowed('new_person_role', NEW_PERSON_ROLES)}",
            name=op.f(f"ck_{table}_new_person_role_allowed"),
        ),
        sa.CheckConstraint(
            "NOT create_people OR new_person_role IS NOT NULL", name=op.f(f"ck_{table}_role_for_new_people")
        ),
    )


def _create_assertions() -> None:
    table = "sso_assertions"
    op.create_table(
        table,
        *_ledger(table),
        sa.Column("connection_id", sa.String(36), nullable=False),
        sa.Column("assertion_key", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        _reference(table, "connection_id", CONNECTIONS),
        sa.UniqueConstraint("assertion_key", name=op.f(f"uq_{table}_assertion_key")),
    )
    op.create_index("ix_sso_assertions_connection", table, ["connection_id", "created_at"])


def _auth_event_kinds(kinds: tuple[str, ...]) -> None:
    op.drop_constraint(op.f("ck_auth_events_kind_allowed"), "auth_events", type_="check")
    op.create_check_constraint(op.f("ck_auth_events_kind_allowed"), "auth_events", allowed("kind", kinds))


def _row_trigger(name: str, event: str, table: str, function: str) -> None:
    _run(f"CREATE TRIGGER {name} BEFORE {event} ON {table} FOR EACH ROW EXECUTE FUNCTION {function}")


def _protect() -> None:
    guarded = ", ".join(f"'{column}'" for column in CONNECTION_COLUMNS)
    _row_trigger("bodha_no_delete", "DELETE", CONNECTIONS, "bodha_reject_change()")
    _row_trigger("bodha_write_once", "UPDATE", CONNECTIONS, f"bodha_write_once({guarded})")
    for table in APPEND_ONLY:
        _row_trigger("bodha_append_only", "UPDATE OR DELETE", table, "bodha_reject_change()")
    for table in NEW_TABLES:
        _row_trigger("bodha_stamp", "INSERT", table, "bodha_stamp('created_at')")
        _run(f"CREATE TRIGGER bodha_no_truncate BEFORE TRUNCATE ON {table} EXECUTE FUNCTION bodha_reject_change()")


def _unprotect() -> None:
    _run(f"DROP TRIGGER bodha_no_delete ON {CONNECTIONS}")
    _run(f"DROP TRIGGER bodha_write_once ON {CONNECTIONS}")
    for table in APPEND_ONLY:
        _run(f"DROP TRIGGER bodha_append_only ON {table}")
    for table in NEW_TABLES:
        _run(f"DROP TRIGGER bodha_stamp ON {table}")
        _run(f"DROP TRIGGER bodha_no_truncate ON {table}")


def _definition(function: str) -> str:
    query = sa.text("SELECT pg_get_functiondef(CAST(:name AS regprocedure))")
    return op.get_bind().scalar(query, {"name": function})


def _runtime_role_exists() -> bool:
    found = op.get_bind().scalar(sa.text("SELECT 1 FROM pg_roles WHERE rolname = :name"), {"name": RUNTIME_ROLE})
    return bool(found)


def upgrade() -> None:
    _create_connections()
    _create_versions()
    _create_assertions()
    op.add_column("sessions", sa.Column("idp_two_step", sa.Boolean(), nullable=False, server_default=sa.false()))
    _auth_event_kinds(AUTH_EVENT_KINDS)
    _protect()
    if _runtime_role_exists():
        _run(f"GRANT SELECT, INSERT, UPDATE ON {CONNECTIONS} TO {RUNTIME_ROLE}")
        _run(f"GRANT SELECT, INSERT ON {', '.join(APPEND_ONLY)} TO {RUNTIME_ROLE}")
    _run(with_steps(_definition(PRACTICE_PURGE), PRACTICE_ANCHOR, PRACTICE_STEPS, PRACTICE_PURGE))
    _run(with_steps(_definition(ORGANIZATION_PURGE), ORGANIZATION_ANCHOR, ORGANIZATION_STEPS, ORGANIZATION_PURGE))


def downgrade() -> None:
    if op.get_bind().scalar(sa.text(KEPT_DATA)):
        raise RuntimeError("single sign-on connections or their auth events exist; 0023 cannot hold them")
    _run(without_steps(_definition(ORGANIZATION_PURGE), ORGANIZATION_STEPS, ORGANIZATION_PURGE))
    _run(without_steps(_definition(PRACTICE_PURGE), PRACTICE_STEPS, PRACTICE_PURGE))
    _unprotect()
    _auth_event_kinds(EARLIER_KINDS)
    op.drop_column("sessions", "idp_two_step")
    for table in reversed(NEW_TABLES):
        op.drop_table(table)
