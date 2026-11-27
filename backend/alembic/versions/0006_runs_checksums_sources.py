import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("batches", "created_by", existing_type=sa.String(36), nullable=True)
    op.add_column("batches", sa.Column("source", sa.String(12), nullable=False, server_default="upload"))
    op.create_check_constraint(op.f("ck_batches_source_allowed"), "batches", "source IN ('upload', 'intake')")
    op.add_column("notes", sa.Column("patient_birth_date", sa.Date(), nullable=True))
    op.add_column("remittances", sa.Column("file_sha256", sa.String(64), nullable=True))
    op.create_index(op.f("ix_remittances_file_sha256"), "remittances", ["file_sha256"])
    _create_audit_runs()
    op.add_column("audit_samples", sa.Column("run_id", sa.String(36), nullable=True))
    op.create_foreign_key(op.f("fk_audit_samples_run_id_audit_runs"), "audit_samples", "audit_runs", ["run_id"], ["id"])
    op.create_index(op.f("ix_audit_samples_run_id"), "audit_samples", ["run_id"])


def _create_audit_runs() -> None:
    op.create_table(
        "audit_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "practice_id",
            sa.String(36),
            sa.ForeignKey("practices.id", name=op.f("fk_audit_runs_practice_id_practices")),
            nullable=False,
        ),
        sa.Column(
            "created_by",
            sa.String(36),
            sa.ForeignKey("users.id", name=op.f("fk_audit_runs_created_by_users")),
            nullable=False,
        ),
        sa.Column("purpose", sa.String(12), nullable=False),
        sa.Column("scope", sa.String(12), nullable=False),
        sa.Column(
            "provider_id",
            sa.String(36),
            sa.ForeignKey("providers.id", name=op.f("fk_audit_runs_provider_id_providers")),
            nullable=True,
        ),
        sa.Column("specialty", sa.String(80), nullable=True),
        sa.Column("period_start", sa.Date(), nullable=True),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column("requested", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(8), nullable=False),
        sa.CheckConstraint("status IN ('open', 'done')", name=op.f("ck_audit_runs_status_allowed")),
        sa.CheckConstraint("purpose IN ('audit', 'training')", name=op.f("ck_audit_runs_purpose_allowed")),
        sa.CheckConstraint("scope IN ('practice', 'provider', 'specialty')", name=op.f("ck_audit_runs_scope_allowed")),
    )
    op.create_index(op.f("ix_audit_runs_practice_id"), "audit_runs", ["practice_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_samples_run_id"), table_name="audit_samples")
    op.drop_constraint(op.f("fk_audit_samples_run_id_audit_runs"), "audit_samples", type_="foreignkey")
    op.drop_column("audit_samples", "run_id")
    op.drop_table("audit_runs")
    op.drop_index(op.f("ix_remittances_file_sha256"), table_name="remittances")
    op.drop_column("remittances", "file_sha256")
    op.drop_column("notes", "patient_birth_date")
    op.drop_constraint(op.f("ck_batches_source_allowed"), "batches", type_="check")
    op.drop_column("batches", "source")
    op.alter_column("batches", "created_by", existing_type=sa.String(36), nullable=False)
