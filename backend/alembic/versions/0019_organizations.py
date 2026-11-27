from pathlib import Path

import sqlalchemy as sa
from alembic import op

revision = "0019"
down_revision = "0017"
branch_labels = None
depends_on = None

FUNCTIONS = Path(__file__).with_name("0019_organizations.sql")
RUNTIME_ROLE = "bodha_runtime"
NOW = sa.text("clock_timestamp()")
PRACTICE_ROLES = "'admin', 'coder', 'cdi', 'compliance', 'biller', 'viewer'"
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
JOIN_KIND = "join_requested"
NEW_TABLES = ("organizations", "organization_memberships", "domain_claims", "domain_join_requests")
PURGE_FUNCTION = "bodha_purge_practice(text, integer)"
ORGANIZATION_PURGE = "bodha_purge_organization(text, integer)"
CLOSURE_FUNCTION = "bodha_organization_closure()"
SUBSCRIPTIONS_STEP = "    'DELETE FROM subscriptions WHERE practice_id = $1',\n"
DOMAIN_STEPS = (
    "    'DELETE FROM domain_join_requests WHERE practice_id = $1',\n"
    "    'DELETE FROM domain_claims WHERE practice_id = $1',\n"
)
OTHER_PRACTICES = "      WHERE other.user_id = member.user_id AND other.practice_id <> practice\n    )\n"
NOT_AN_ORGANIZATION_ADMIN = (
    "      WHERE other.user_id = member.user_id AND other.practice_id <> practice\n"
    "    ) AND NOT EXISTS (\n"
    "      SELECT 1 FROM organization_memberships AS org_member WHERE org_member.user_id = member.user_id\n"
    "    )\n"
)
KEPT_DATA = (
    "SELECT (SELECT count(*) FROM organizations) + (SELECT count(*) FROM domain_claims)"
    " + (SELECT count(*) FROM inbox_items WHERE kind = 'join_requested')"
)


def _run(statement: str) -> None:
    op.get_bind().exec_driver_sql(statement)


def _ledger(table: str) -> list[sa.SchemaItem]:
    return [
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{table}")),
    ]


def _reference(table: str, column: str, target: str, *, on_delete: str | None = None) -> sa.ForeignKeyConstraint:
    name = op.f(f"fk_{table}_{column}_{target}")
    return sa.ForeignKeyConstraint([column], [f"{target}.id"], name=name, ondelete=on_delete)


def _create_organizations() -> None:
    op.create_table(
        "organizations",
        *_ledger("organizations"),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("plan", sa.String(16), nullable=False),
        sa.Column("renews_on", sa.Date(), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_by", sa.String(36), nullable=True),
        sa.Column("purged_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('active', 'closed', 'purged')", name=op.f("ck_organizations_status_allowed")),
        sa.CheckConstraint(
            "(status IN ('closed', 'purged')) = (closed_at IS NOT NULL)",
            name=op.f("ck_organizations_closed_when_closed_at"),
        ),
    )


def _create_memberships() -> None:
    table = "organization_memberships"
    op.create_table(
        table,
        *_ledger(table),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("realm", sa.String(16), nullable=False, server_default="practice"),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("added_by", sa.String(36), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id", "realm"], ["users.id", "users.realm"], name=op.f(f"fk_{table}_user_id_users")
        ),
        _reference(table, "organization_id", "organizations"),
        _reference(table, "added_by", "users", on_delete="SET NULL"),
        sa.UniqueConstraint("user_id", "organization_id", name=op.f(f"uq_{table}_user_id")),
        sa.CheckConstraint("realm = 'practice'", name=op.f(f"ck_{table}_realm_practice")),
        sa.CheckConstraint("role IN ('admin')", name=op.f(f"ck_{table}_role_allowed")),
    )
    op.create_index("ix_organization_memberships_organization", table, ["organization_id", "role"])


def _claim_columns() -> list[sa.Column]:
    return [
        sa.Column("domain", sa.String(253), nullable=False),
        sa.Column("practice_id", sa.String(36), nullable=False),
        sa.Column("organization_id", sa.String(36), nullable=True),
        sa.Column("claimed_by", sa.String(36), nullable=True),
        sa.Column("token", sa.String(64), nullable=False),
        sa.Column("email_token_hash", sa.String(64), nullable=True),
        sa.Column("email_sent_to", sa.String(320), nullable=True),
        sa.Column("email_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_via", sa.String(8), nullable=True),
        sa.Column("join_mode", sa.String(8), nullable=False),
        sa.Column("join_role", sa.String(16), nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("released_by", sa.String(36), nullable=True),
    ]


def _create_claims() -> None:
    table = "domain_claims"
    op.create_table(
        table,
        *_ledger(table),
        *_claim_columns(),
        _reference(table, "practice_id", "practices"),
        _reference(table, "organization_id", "organizations"),
        _reference(table, "claimed_by", "users", on_delete="SET NULL"),
        sa.UniqueConstraint("email_token_hash", name=op.f(f"uq_{table}_email_token_hash")),
        sa.CheckConstraint("join_mode IN ('off', 'request', 'auto')", name=op.f(f"ck_{table}_join_mode_allowed")),
        sa.CheckConstraint(f"join_role IN ({PRACTICE_ROLES})", name=op.f(f"ck_{table}_join_role_allowed")),
        sa.CheckConstraint(
            "verified_via IS NULL OR verified_via IN ('dns', 'email')", name=op.f(f"ck_{table}_verified_via_allowed")
        ),
        sa.CheckConstraint(
            "(verified_at IS NULL) = (verified_via IS NULL)", name=op.f(f"ck_{table}_verified_with_method")
        ),
    )
    op.create_index(
        "uq_domain_claims_verified_domain",
        table,
        ["domain"],
        unique=True,
        postgresql_where=sa.text("verified_at IS NOT NULL AND released_at IS NULL"),
    )
    op.create_index("ix_domain_claims_practice", table, ["practice_id"])
    op.create_index("ix_domain_claims_organization", table, ["organization_id"])


def _create_join_requests() -> None:
    table = "domain_join_requests"
    op.create_table(
        table,
        *_ledger(table),
        sa.Column("claim_id", sa.String(36), nullable=False),
        sa.Column("practice_id", sa.String(36), nullable=False),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column("role", sa.String(16), nullable=True),
        sa.Column("user_id", sa.String(36), nullable=True),
        sa.Column("decided_by", sa.String(36), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        _reference(table, "claim_id", "domain_claims"),
        _reference(table, "practice_id", "practices"),
        _reference(table, "user_id", "users", on_delete="SET NULL"),
        _reference(table, "decided_by", "users", on_delete="SET NULL"),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'declined', 'joined')", name=op.f(f"ck_{table}_status_allowed")
        ),
        sa.CheckConstraint(f"role IS NULL OR role IN ({PRACTICE_ROLES})", name=op.f(f"ck_{table}_role_allowed")),
    )
    op.create_index(
        "uq_domain_join_requests_pending",
        table,
        ["practice_id", "email"],
        unique=True,
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.create_index("ix_domain_join_requests_practice", table, ["practice_id", "status", "created_at"])


def _attach_practices_and_subscriptions() -> None:
    op.add_column("practices", sa.Column("organization_id", sa.String(36), nullable=True))
    op.add_column(
        "practices", sa.Column("combined_billing", sa.Boolean(), nullable=False, server_default=sa.text("false"))
    )
    op.create_foreign_key(
        op.f("fk_practices_organization_id_organizations"), "practices", "organizations", ["organization_id"], ["id"]
    )
    op.create_index(op.f("ix_practices_organization_id"), "practices", ["organization_id"])
    op.create_check_constraint(
        op.f("ck_practices_combined_in_organization"),
        "practices",
        "NOT combined_billing OR organization_id IS NOT NULL",
    )
    op.add_column("subscriptions", sa.Column("organization_id", sa.String(36), nullable=True))
    op.create_foreign_key(
        op.f("fk_subscriptions_organization_id_organizations"),
        "subscriptions",
        "organizations",
        ["organization_id"],
        ["id"],
    )
    op.create_unique_constraint(op.f("uq_subscriptions_organization_id"), "subscriptions", ["organization_id"])
    op.alter_column("subscriptions", "practice_id", existing_type=sa.String(36), nullable=True)
    op.create_check_constraint(
        op.f("ck_subscriptions_one_owner"), "subscriptions", "(practice_id IS NULL) <> (organization_id IS NULL)"
    )


def _inbox_kinds(kinds: tuple[str, ...]) -> None:
    allowed = ", ".join(f"'{kind}'" for kind in kinds)
    op.drop_constraint(op.f("ck_inbox_items_kind_allowed"), "inbox_items", type_="check")
    op.create_check_constraint(op.f("ck_inbox_items_kind_allowed"), "inbox_items", f"kind IN ({allowed})")


def _row_trigger(name: str, event: str, table: str, function: str) -> None:
    _run(f"CREATE TRIGGER {name} BEFORE {event} ON {table} FOR EACH ROW EXECUTE FUNCTION {function}")


def _protect(table: str) -> None:
    _row_trigger("bodha_no_delete", "DELETE", table, "bodha_reject_change()")
    _row_trigger("bodha_stamp", "INSERT", table, "bodha_stamp('created_at')")
    _run(f"CREATE TRIGGER bodha_no_truncate BEFORE TRUNCATE ON {table} EXECUTE FUNCTION bodha_reject_change()")


def _purge_definition(*, holding: tuple[str, ...]) -> str:
    query = sa.text("SELECT pg_get_functiondef(CAST(:name AS regprocedure))")
    definition = op.get_bind().scalar(query, {"name": PURGE_FUNCTION})
    if any(definition.count(text) != 1 for text in holding):
        raise RuntimeError(f"{PURGE_FUNCTION} no longer reads as this migration expects")
    return definition


def purge_with_organizations(definition: str) -> str:
    with_steps = definition.replace(SUBSCRIPTIONS_STEP, DOMAIN_STEPS + SUBSCRIPTIONS_STEP, 1)
    return with_steps.replace(OTHER_PRACTICES, NOT_AN_ORGANIZATION_ADMIN, 1)


def purge_without_organizations(definition: str) -> str:
    without_steps = definition.replace(DOMAIN_STEPS, "", 1)
    return without_steps.replace(NOT_AN_ORGANIZATION_ADMIN, OTHER_PRACTICES, 1)


def _runtime_role_exists() -> bool:
    found = op.get_bind().scalar(sa.text("SELECT 1 FROM pg_roles WHERE rolname = :name"), {"name": RUNTIME_ROLE})
    return bool(found)


def _grant_runtime() -> None:
    _run(f"GRANT SELECT, INSERT, UPDATE ON {', '.join(NEW_TABLES)} TO {RUNTIME_ROLE}")
    _run(f"GRANT EXECUTE ON FUNCTION {ORGANIZATION_PURGE} TO {RUNTIME_ROLE}")


def upgrade() -> None:
    _create_organizations()
    _create_memberships()
    _attach_practices_and_subscriptions()
    _create_claims()
    _create_join_requests()
    _inbox_kinds((*INBOX_KINDS, JOIN_KIND))
    for statement in FUNCTIONS.read_text(encoding="utf-8").split("\n;\n"):
        if statement.strip():
            _run(statement)
    _row_trigger("bodha_closure", "INSERT OR UPDATE", "organizations", CLOSURE_FUNCTION)
    for table in NEW_TABLES:
        _protect(table)
    _run(f"REVOKE ALL ON FUNCTION {ORGANIZATION_PURGE} FROM PUBLIC")
    purge = _purge_definition(holding=(SUBSCRIPTIONS_STEP, OTHER_PRACTICES))
    _run(purge_with_organizations(purge))
    if _runtime_role_exists():
        _grant_runtime()


def downgrade() -> None:
    kept = op.get_bind().scalar(sa.text(KEPT_DATA))
    if kept:
        raise RuntimeError("organizations, domain claims or join requests exist; the earlier schema cannot hold them")
    _run(purge_without_organizations(_purge_definition(holding=(DOMAIN_STEPS, NOT_AN_ORGANIZATION_ADMIN))))
    for table in NEW_TABLES:
        for trigger in ("bodha_no_delete", "bodha_stamp", "bodha_no_truncate"):
            _run(f"DROP TRIGGER {trigger} ON {table}")
    _run("DROP TRIGGER bodha_closure ON organizations")
    _run(f"DROP FUNCTION {ORGANIZATION_PURGE}")
    _run(f"DROP FUNCTION {CLOSURE_FUNCTION}")
    _inbox_kinds(INBOX_KINDS)
    op.drop_table("domain_join_requests")
    op.drop_table("domain_claims")
    op.drop_constraint(op.f("ck_subscriptions_one_owner"), "subscriptions", type_="check")
    op.alter_column("subscriptions", "practice_id", existing_type=sa.String(36), nullable=False)
    op.drop_constraint(op.f("uq_subscriptions_organization_id"), "subscriptions", type_="unique")
    op.drop_constraint(op.f("fk_subscriptions_organization_id_organizations"), "subscriptions", type_="foreignkey")
    op.drop_column("subscriptions", "organization_id")
    op.drop_constraint(op.f("ck_practices_combined_in_organization"), "practices", type_="check")
    op.drop_index(op.f("ix_practices_organization_id"), table_name="practices")
    op.drop_constraint(op.f("fk_practices_organization_id_organizations"), "practices", type_="foreignkey")
    op.drop_column("practices", "combined_billing")
    op.drop_column("practices", "organization_id")
    op.drop_table("organization_memberships")
    op.drop_table("organizations")
