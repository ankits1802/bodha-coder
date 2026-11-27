import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def _id_columns() -> list[sa.Column]:
    return [
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    ]


def _json(name: str, default: str) -> sa.Column:
    return sa.Column(name, JSONB(), nullable=False, server_default=sa.text(f"'{default}'::jsonb"))


def upgrade() -> None:
    op.add_column("practices", _json("intake", "{}"))
    op.add_column("providers", sa.Column("auto_approve", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("notes", sa.Column("payer", sa.String(64), nullable=True))
    op.add_column("addendum_requests", sa.Column("escalated_at", sa.DateTime(timezone=True), nullable=True))
    _create_audit_samples()
    _create_eval_cases()
    _create_eval_runs()
    _create_remittances()
    _create_remittance_lines()


def _create_audit_samples() -> None:
    op.create_table(
        "audit_samples",
        *_id_columns(),
        sa.Column(
            "practice_id",
            sa.String(36),
            sa.ForeignKey("practices.id", name=op.f("fk_audit_samples_practice_id_practices")),
            nullable=False,
        ),
        sa.Column(
            "note_id",
            sa.String(36),
            sa.ForeignKey("notes.id", name=op.f("fk_audit_samples_note_id_notes")),
            nullable=False,
        ),
        sa.Column(
            "analysis_id",
            sa.String(36),
            sa.ForeignKey("analyses.id", name=op.f("fk_audit_samples_analysis_id_analyses")),
            nullable=True,
        ),
        sa.Column(
            "reviewer_id",
            sa.String(36),
            sa.ForeignKey("users.id", name=op.f("fk_audit_samples_reviewer_id_users")),
            nullable=False,
        ),
        sa.Column("purpose", sa.String(12), nullable=False),
        sa.Column("status", sa.String(8), nullable=False),
        _json("answer", "{}"),
        _json("result", "{}"),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('open', 'done')", name=op.f("ck_audit_samples_status_allowed")),
        sa.CheckConstraint("purpose IN ('audit', 'training')", name=op.f("ck_audit_samples_purpose_allowed")),
    )
    for column in ("practice_id", "note_id", "reviewer_id"):
        op.create_index(op.f(f"ix_audit_samples_{column}"), "audit_samples", [column])


def _create_eval_cases() -> None:
    op.create_table(
        "eval_cases",
        *_id_columns(),
        sa.Column(
            "practice_id",
            sa.String(36),
            sa.ForeignKey("practices.id", name=op.f("fk_eval_cases_practice_id_practices")),
            nullable=False,
        ),
        sa.Column(
            "note_id",
            sa.String(36),
            sa.ForeignKey("notes.id", name=op.f("fk_eval_cases_note_id_notes")),
            nullable=False,
        ),
        _json("expected", "{}"),
        sa.Column(
            "created_by",
            sa.String(36),
            sa.ForeignKey("users.id", name=op.f("fk_eval_cases_created_by_users")),
            nullable=False,
        ),
        sa.UniqueConstraint("practice_id", "note_id", name=op.f("uq_eval_cases_practice_id")),
    )
    op.create_index(op.f("ix_eval_cases_practice_id"), "eval_cases", ["practice_id"])


def _create_eval_runs() -> None:
    op.create_table(
        "eval_runs",
        *_id_columns(),
        sa.Column(
            "practice_id",
            sa.String(36),
            sa.ForeignKey("practices.id", name=op.f("fk_eval_runs_practice_id_practices")),
            nullable=False,
        ),
        sa.Column("model", sa.String(80), nullable=False),
        sa.Column("prompt_version", sa.String(40), nullable=False),
        sa.Column("status", sa.String(8), nullable=False),
        _json("results", "[]"),
        _json("summary", "{}"),
        sa.Column(
            "requested_by",
            sa.String(36),
            sa.ForeignKey("users.id", name=op.f("fk_eval_runs_requested_by_users")),
            nullable=True,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'done', 'failed')", name=op.f("ck_eval_runs_status_allowed")
        ),
    )
    op.create_index(op.f("ix_eval_runs_practice_id"), "eval_runs", ["practice_id"])


def _create_remittances() -> None:
    op.create_table(
        "remittances",
        *_id_columns(),
        sa.Column(
            "practice_id",
            sa.String(36),
            sa.ForeignKey("practices.id", name=op.f("fk_remittances_practice_id_practices")),
            nullable=False,
        ),
        sa.Column("file_key", sa.String(300), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("payer", sa.String(120), nullable=True),
        sa.Column("paid_on", sa.Date(), nullable=True),
        sa.Column(
            "uploaded_by",
            sa.String(36),
            sa.ForeignKey("users.id", name=op.f("fk_remittances_uploaded_by_users")),
            nullable=False,
        ),
    )
    op.create_index(op.f("ix_remittances_practice_id"), "remittances", ["practice_id"])


def _create_remittance_lines() -> None:
    op.create_table(
        "remittance_lines",
        *_id_columns(),
        sa.Column(
            "remittance_id",
            sa.String(36),
            sa.ForeignKey("remittances.id", name=op.f("fk_remittance_lines_remittance_id_remittances")),
            nullable=False,
        ),
        sa.Column(
            "note_id",
            sa.String(36),
            sa.ForeignKey("notes.id", name=op.f("fk_remittance_lines_note_id_notes")),
            nullable=True,
        ),
        sa.Column("claim_ref", sa.String(80), nullable=True),
        sa.Column("patient_name", sa.String(200), nullable=True),
        sa.Column("service_date", sa.Date(), nullable=True),
        sa.Column("billed_code", sa.String(16), nullable=True),
        sa.Column("paid_code", sa.String(16), nullable=True),
        sa.Column("billed_amount", sa.Integer(), nullable=True),
        sa.Column("paid_amount", sa.Integer(), nullable=True),
        _json("adjustments", "[]"),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("appeal_by", sa.Date(), nullable=True),
        sa.CheckConstraint(
            "status IN ('matched', 'unmatched', 'downcoded', 'denied', 'paid_as_billed')",
            name=op.f("ck_remittance_lines_status_allowed"),
        ),
    )
    op.create_index(op.f("ix_remittance_lines_remittance_id"), "remittance_lines", ["remittance_id"])
    op.create_index(op.f("ix_remittance_lines_note_id"), "remittance_lines", ["note_id"])


def downgrade() -> None:
    for table in ("remittance_lines", "remittances", "eval_runs", "eval_cases", "audit_samples"):
        op.drop_table(table)
    op.drop_column("addendum_requests", "escalated_at")
    op.drop_column("notes", "payer")
    op.drop_column("providers", "auto_approve")
    op.drop_column("practices", "intake")
