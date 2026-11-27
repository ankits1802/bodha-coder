import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0016"
down_revision = "0013"
branch_labels = None
depends_on = None

SEALED_TABLES = ("signatures", "signature_adoptions", "signing_events")
ONE_OWNER = "(user_id IS NULL) <> (provider_id IS NULL)"
PROVIDER_IN_PRACTICE = "provider_id IS NULL OR practice_id IS NOT NULL"
REFUSE_CHANGE = """
CREATE FUNCTION refuse_sealed_record_change() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'DELETE' AND current_setting('bodha.erasure', true) = 'on' THEN
        RETURN OLD;
    END IF;
    RAISE EXCEPTION '% rows are sealed records and are never changed or deleted', TG_TABLE_NAME;
END
$$
"""


def _keyed() -> list[sa.Column]:
    return [
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    ]


def _owner(table: str) -> list[sa.SchemaItem]:
    return [
        sa.Column("practice_id", sa.String(36), nullable=True),
        sa.Column("user_id", sa.String(36), nullable=True),
        sa.Column("provider_id", sa.String(36), nullable=True),
        sa.ForeignKeyConstraint(["practice_id"], ["practices.id"], name=op.f(f"fk_{table}_practice_id_practices")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f(f"fk_{table}_user_id_users")),
        sa.ForeignKeyConstraint(["provider_id"], ["providers.id"], name=op.f(f"fk_{table}_provider_id_providers")),
        sa.CheckConstraint(ONE_OWNER, name=op.f(f"ck_{table}_one_owner")),
        sa.CheckConstraint(PROVIDER_IN_PRACTICE, name=op.f(f"ck_{table}_provider_in_practice")),
    ]


def _owner_indexes(table: str) -> None:
    op.create_index(f"ix_{table}_user", table, ["user_id", "created_at"])
    op.create_index(f"ix_{table}_provider", table, ["provider_id", "created_at"])


def _create_signatures() -> None:
    table = "signatures"
    op.create_table(
        table,
        *_keyed(),
        sa.Column("source", sa.String(12), nullable=False),
        sa.Column("typed_name", sa.String(120), nullable=False),
        sa.Column("file_key", sa.String(300), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("file_bytes", sa.Integer(), nullable=False),
        sa.Column("checked", sa.Boolean(), nullable=False),
        sa.Column("check", JSONB(), nullable=True),
        sa.Column("ip", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.String(300), nullable=True),
        *_owner(table),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{table}")),
        sa.CheckConstraint("source IN ('drawn', 'typed', 'uploaded')", name=op.f(f"ck_{table}_source_allowed")),
    )
    _owner_indexes(table)


def _create_adoptions() -> None:
    table = "signature_adoptions"
    op.create_table(
        table,
        *_keyed(),
        sa.Column("signature_id", sa.String(36), nullable=False),
        *_owner(table),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{table}")),
        sa.ForeignKeyConstraint(["signature_id"], ["signatures.id"], name=op.f(f"fk_{table}_signature_id_signatures")),
    )
    _owner_indexes(table)


def _signer_columns() -> list[sa.Column]:
    return [
        sa.Column("signer_kind", sa.String(8), nullable=False),
        sa.Column("signer_user_id", sa.String(36), nullable=True),
        sa.Column("signer_provider_id", sa.String(36), nullable=True),
        sa.Column("signer_name", sa.String(120), nullable=False),
        sa.Column("signer_title", sa.String(60), nullable=False),
        sa.Column("typed_name", sa.String(120), nullable=False),
        sa.Column("signature_id", sa.String(36), nullable=True),
        sa.Column("signature_sha256", sa.String(64), nullable=True),
    ]


def _seal_columns() -> list[sa.Column]:
    return [
        sa.Column("code", sa.String(16), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("envelope", sa.Text(), nullable=False),
        sa.Column("envelope_sha256", sa.String(64), nullable=False),
        sa.Column("seal", sa.Text(), nullable=False),
        sa.Column("seal_key_id", sa.String(300), nullable=False),
        sa.Column("seal_algorithm", sa.String(20), nullable=False),
    ]


def _event_references(table: str) -> list[sa.SchemaItem]:
    references = (
        ("practice_id", "practices"),
        ("note_id", "notes"),
        ("signer_user_id", "users"),
        ("signer_provider_id", "providers"),
        ("signature_id", "signatures"),
    )
    return [
        sa.ForeignKeyConstraint([column], [f"{target}.id"], name=op.f(f"fk_{table}_{column}_{target}"))
        for column, target in references
    ]


def _create_signing_events() -> None:
    table = "signing_events"
    op.create_table(
        table,
        *_keyed(),
        sa.Column("practice_id", sa.String(36), nullable=False),
        sa.Column("note_id", sa.String(36), nullable=True),
        sa.Column("event", sa.String(24), nullable=False),
        sa.Column("record_id", sa.String(36), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        *_signer_columns(),
        sa.Column("document_sha256", sa.String(64), nullable=True),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ip", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.String(300), nullable=True),
        *_seal_columns(),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{table}")),
        *_event_references(table),
        sa.UniqueConstraint("code", name=op.f(f"uq_{table}_code")),
        sa.CheckConstraint(
            "event IN ('approval', 'compliance_decision', 'provider_addendum', 'provider_level_change', 'agreement')",
            name=op.f(f"ck_{table}_event_allowed"),
        ),
        sa.CheckConstraint("signer_kind IN ('user', 'provider')", name=op.f(f"ck_{table}_signer_kind_allowed")),
        sa.CheckConstraint(
            "(signer_user_id IS NULL) <> (signer_provider_id IS NULL)", name=op.f(f"ck_{table}_one_signer")
        ),
    )
    op.create_index("ix_signing_events_note", table, ["note_id", "signed_at"])
    op.create_index("ix_signing_events_practice", table, ["practice_id", "signed_at"])


def upgrade() -> None:
    _create_signatures()
    _create_adoptions()
    _create_signing_events()
    op.execute(REFUSE_CHANGE)
    for table in SEALED_TABLES:
        op.execute(
            f"CREATE TRIGGER {table}_sealed BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION refuse_sealed_record_change()"
        )


def downgrade() -> None:
    for table in SEALED_TABLES:
        op.execute(f"DROP TRIGGER {table}_sealed ON {table}")
    op.execute("DROP FUNCTION refuse_sealed_record_change()")
    op.drop_table("signing_events")
    op.drop_table("signature_adoptions")
    op.drop_table("signatures")
