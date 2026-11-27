import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None

OVERRIDE_REASON_ALLOWED = (
    "override_reason IS NULL OR override_reason IN ('documentation', 'payer_policy', 'provider_answer', "
    "'coding_guideline', 'clinical_context', 'other')"
)
OTHER_NEEDS_NOTE = "override_reason IS DISTINCT FROM 'other' OR length(btrim(coalesce(override_note, ''))) > 0"
OVERRIDDEN_TABLES = ("decisions", "code_sets")
APPEND_ONLY_TABLES = (
    "approved_claims",
    "claim_exports",
    "claim_export_items",
    "provider_attestations",
    "review_comments",
    "review_comment_removals",
    "audit_packages",
)
REFUSE_UPDATE = """
CREATE FUNCTION refuse_review_record_update() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION '% rows are append-only and are never updated', TG_TABLE_NAME;
END
$$
"""
BACKFILL_SNAPSHOTS = """
INSERT INTO approved_claims (
    id, created_at, practice_id, note_id, revision, final_code_set_id, approved_by, approver_name, approver_role,
    approved_at, analysis_id, model, prompt_version, text_revision_ids, document_key, document_sha256,
    schema_version, content
)
SELECT
    gen_random_uuid()::text, now(), n.practice_id, n.id, 1, f.id, n.approved_by,
    coalesce(u.name, 'Bodha (auto)'), coalesce(u.role, 'system'), coalesce(n.approved_at, f.created_at),
    a.id, a.model, a.prompt_version, '[]'::jsonb, n.file_key, n.file_sha256, 1,
    jsonb_build_object(
        'codes', f.codes,
        'billed', coalesce(b.codes, '[]'::jsonb),
        'billed_revision', coalesce(b.revision, 0),
        'billed_original', coalesce(b1.codes, '[]'::jsonb),
        'decisions', '[]'::jsonb,
        'backfilled', true
    )
FROM notes n
JOIN LATERAL (
    SELECT id, codes, created_at FROM code_sets WHERE note_id = n.id AND kind = 'final' ORDER BY revision DESC LIMIT 1
) f ON true
LEFT JOIN LATERAL (
    SELECT codes, revision FROM code_sets WHERE note_id = n.id AND kind = 'billed' ORDER BY revision DESC LIMIT 1
) b ON true
LEFT JOIN LATERAL (
    SELECT codes FROM code_sets WHERE note_id = n.id AND kind = 'billed' ORDER BY revision LIMIT 1
) b1 ON true
LEFT JOIN users u ON u.id = n.approved_by
LEFT JOIN analyses a ON a.id = n.current_analysis_id
WHERE n.status IN ('approved', 'exported')
"""


def _keyed() -> list[sa.Column]:
    return [
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("practice_id", sa.String(36), nullable=False),
    ]


def _owned(table: str, *references: tuple[str, str]) -> list[sa.SchemaItem]:
    items: list[sa.SchemaItem] = [
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{table}")),
        sa.ForeignKeyConstraint(["practice_id"], ["practices.id"], name=op.f(f"fk_{table}_practice_id_practices")),
    ]
    for column, target in references:
        referred = target.split(".")[0]
        items.append(
            sa.ForeignKeyConstraint([column], [target], name=op.f(f"fk_{table}_{column}_{referred}")),
        )
    return items


def _actor(prefix: str) -> list[sa.Column]:
    return [
        sa.Column(f"{prefix}_name", sa.String(120), nullable=False),
        sa.Column(f"{prefix}_role", sa.String(16), nullable=False),
    ]


def _client() -> list[sa.Column]:
    return [sa.Column("ip", sa.String(64), nullable=True), sa.Column("user_agent", sa.String(300), nullable=True)]


def _stored_file() -> list[sa.Column]:
    return [
        sa.Column("file_key", sa.String(300), nullable=False),
        sa.Column("file_sha256", sa.String(64), nullable=False),
        sa.Column("file_bytes", sa.Integer(), nullable=False),
    ]


def _create_approved_claims() -> None:
    table = "approved_claims"
    op.create_table(
        table,
        *_keyed(),
        sa.Column("note_id", sa.String(36), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("final_code_set_id", sa.String(36), nullable=False),
        sa.Column("approved_by", sa.String(36), nullable=True),
        *_actor("approver"),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("analysis_id", sa.String(36), nullable=True),
        sa.Column("model", sa.String(60), nullable=True),
        sa.Column("prompt_version", sa.String(20), nullable=True),
        sa.Column("text_revision_ids", JSONB(), nullable=False),
        sa.Column("document_key", sa.String(300), nullable=False),
        sa.Column("document_sha256", sa.String(64), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("content", JSONB(), nullable=False),
        *_owned(
            table,
            ("note_id", "notes.id"),
            ("final_code_set_id", "code_sets.id"),
            ("approved_by", "users.id"),
            ("analysis_id", "analyses.id"),
        ),
        sa.UniqueConstraint("note_id", "revision", name=op.f("uq_approved_claims_note_id")),
    )
    op.create_index("ix_approved_claims_practice", table, ["practice_id"])


def _create_exports() -> None:
    op.create_table(
        "claim_exports",
        *_keyed(),
        sa.Column("format", sa.String(20), nullable=False),
        sa.Column("again", sa.Boolean(), nullable=False),
        sa.Column("actor_id", sa.String(36), nullable=False),
        *_actor("actor"),
        *_stored_file(),
        sa.Column("file_name", sa.String(120), nullable=False),
        sa.Column("notes_count", sa.Integer(), nullable=False),
        *_client(),
        *_owned("claim_exports", ("actor_id", "users.id")),
        sa.CheckConstraint(
            "format IN ('csv', 'claim_lines_csv', 'claim_lines_json')", name=op.f("ck_claim_exports_format_allowed")
        ),
    )
    op.create_index("ix_claim_exports_practice", "claim_exports", ["practice_id", "created_at"])
    op.create_table(
        "claim_export_items",
        *_keyed(),
        sa.Column("export_id", sa.String(36), nullable=False),
        sa.Column("note_id", sa.String(36), nullable=False),
        sa.Column("approved_claim_id", sa.String(36), nullable=False),
        sa.Column("snapshot_revision", sa.Integer(), nullable=False),
        *_owned(
            "claim_export_items",
            ("export_id", "claim_exports.id"),
            ("note_id", "notes.id"),
            ("approved_claim_id", "approved_claims.id"),
        ),
        sa.UniqueConstraint("export_id", "note_id", name=op.f("uq_claim_export_items_export_id")),
    )
    op.create_index("ix_claim_export_items_note", "claim_export_items", ["note_id"])


def _create_attestations() -> None:
    table = "provider_attestations"
    op.create_table(
        table,
        *_keyed(),
        sa.Column("note_id", sa.String(36), nullable=False),
        sa.Column("request_id", sa.String(36), nullable=False),
        sa.Column("provider_id", sa.String(36), nullable=False),
        sa.Column("approved_claim_id", sa.String(36), nullable=True),
        sa.Column("purpose", sa.String(12), nullable=False),
        sa.Column("wording", sa.Text(), nullable=False),
        sa.Column("confirmed", sa.Boolean(), nullable=False),
        sa.Column("text_revision_ids", JSONB(), nullable=False),
        sa.Column("shown", sa.Text(), nullable=False),
        sa.Column("answer", sa.String(12), nullable=False),
        sa.Column("comment", sa.String(2000), nullable=True),
        *_client(),
        *_owned(
            table,
            ("note_id", "notes.id"),
            ("request_id", "addendum_requests.id"),
            ("provider_id", "providers.id"),
            ("approved_claim_id", "approved_claims.id"),
        ),
        sa.CheckConstraint(
            "purpose IN ('questions', 'level_change')", name=op.f("ck_provider_attestations_purpose_allowed")
        ),
        sa.CheckConstraint(
            "answer IN ('signed', 'confirm', 'disagree')", name=op.f("ck_provider_attestations_answer_allowed")
        ),
        sa.CheckConstraint("confirmed", name=op.f("ck_provider_attestations_confirmed_ticked")),
    )
    op.create_index("ix_provider_attestations_note", table, ["note_id", "created_at"])


def _create_comments() -> None:
    op.create_table(
        "review_comments",
        *_keyed(),
        sa.Column("note_id", sa.String(36), nullable=False),
        sa.Column("finding_key", sa.String(80), nullable=True),
        sa.Column("body", sa.String(2000), nullable=False),
        sa.Column("author_id", sa.String(36), nullable=False),
        *_actor("author"),
        sa.Column("mentions", JSONB(), nullable=False),
        *_owned("review_comments", ("note_id", "notes.id"), ("author_id", "users.id")),
    )
    op.create_index("ix_review_comments_note", "review_comments", ["note_id", "created_at"])
    op.create_table(
        "review_comment_removals",
        *_keyed(),
        sa.Column("note_id", sa.String(36), nullable=False),
        sa.Column("comment_id", sa.String(36), nullable=False),
        sa.Column("removed_by", sa.String(36), nullable=False),
        *_actor("remover"),
        *_owned(
            "review_comment_removals",
            ("note_id", "notes.id"),
            ("comment_id", "review_comments.id"),
            ("removed_by", "users.id"),
        ),
        sa.UniqueConstraint("comment_id", name=op.f("uq_review_comment_removals_comment_id")),
    )
    op.create_index(op.f("ix_review_comment_removals_note_id"), "review_comment_removals", ["note_id"])


def _create_audit_packages() -> None:
    op.create_table(
        "audit_packages",
        *_keyed(),
        sa.Column("note_id", sa.String(36), nullable=False),
        *_stored_file(),
        sa.Column("file_count", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.String(36), nullable=False),
        *_actor("actor"),
        *_client(),
        *_owned("audit_packages", ("note_id", "notes.id"), ("actor_id", "users.id")),
    )
    op.create_index("ix_audit_packages_note", "audit_packages", ["note_id", "created_at"])


def _add_override_columns() -> None:
    for table in OVERRIDDEN_TABLES:
        op.add_column(table, sa.Column("actor_role", sa.String(16), nullable=True))
        op.add_column(table, sa.Column("override_reason", sa.String(24), nullable=True))
        op.add_column(table, sa.Column("override_note", sa.String(500), nullable=True))
        op.create_check_constraint(op.f(f"ck_{table}_override_reason_allowed"), table, OVERRIDE_REASON_ALLOWED)
        op.create_check_constraint(op.f(f"ck_{table}_override_other_noted"), table, OTHER_NEEDS_NOTE)


def _add_request_and_practice_columns() -> None:
    op.add_column(
        "addendum_requests",
        sa.Column("purpose", sa.String(12), nullable=False, server_default=sa.text("'questions'")),
    )
    op.add_column("addendum_requests", sa.Column("approved_claim_id", sa.String(36), nullable=True))
    op.create_check_constraint(
        op.f("ck_addendum_requests_purpose_allowed"), "addendum_requests", "purpose IN ('questions', 'level_change')"
    )
    op.create_foreign_key(
        op.f("fk_addendum_requests_approved_claim_id_approved_claims"),
        "addendum_requests",
        "approved_claims",
        ["approved_claim_id"],
        ["id"],
    )
    for column in ("confirm_level_changes", "hold_until_confirmed"):
        op.add_column("practices", sa.Column(column, sa.Boolean(), nullable=False, server_default=sa.false()))


def upgrade() -> None:
    _add_override_columns()
    _create_approved_claims()
    _create_exports()
    _add_request_and_practice_columns()
    _create_attestations()
    _create_comments()
    _create_audit_packages()
    op.execute(BACKFILL_SNAPSHOTS)
    op.execute(REFUSE_UPDATE)
    for table in APPEND_ONLY_TABLES:
        op.execute(
            f"CREATE TRIGGER {table}_append_only BEFORE UPDATE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION refuse_review_record_update()"
        )


def downgrade() -> None:
    for table in APPEND_ONLY_TABLES:
        op.execute(f"DROP TRIGGER {table}_append_only ON {table}")
    op.execute("DROP FUNCTION refuse_review_record_update()")
    for column in ("hold_until_confirmed", "confirm_level_changes"):
        op.drop_column("practices", column)
    op.drop_table("audit_packages")
    op.drop_table("review_comment_removals")
    op.drop_table("review_comments")
    op.drop_table("provider_attestations")
    op.drop_constraint(
        op.f("fk_addendum_requests_approved_claim_id_approved_claims"), "addendum_requests", type_="foreignkey"
    )
    op.drop_constraint(op.f("ck_addendum_requests_purpose_allowed"), "addendum_requests", type_="check")
    op.drop_column("addendum_requests", "approved_claim_id")
    op.drop_column("addendum_requests", "purpose")
    op.drop_table("claim_export_items")
    op.drop_table("claim_exports")
    op.drop_table("approved_claims")
    for table in OVERRIDDEN_TABLES:
        op.drop_constraint(op.f(f"ck_{table}_override_other_noted"), table, type_="check")
        op.drop_constraint(op.f(f"ck_{table}_override_reason_allowed"), table, type_="check")
        op.drop_column(table, "override_note")
        op.drop_column(table, "override_reason")
        op.drop_column(table, "actor_role")
