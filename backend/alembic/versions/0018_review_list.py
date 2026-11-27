import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None

TABLE = "note_returns"
RUNTIME_ROLE = "bodha_runtime"
PURGE_FUNCTION = "bodha_purge_practice(text, integer)"
LANE_REASON_CHECK = "ck_notes_lane_reason_allowed"
EARLIER_LANE_REASONS = (
    "flagged",
    "levels_too_high",
    "audit_risk",
    "waiting_on_provider",
    "code_changes",
    "questions",
    "matches",
)
RETURNED = "returned"
RETURN_REASONS = (
    "level_not_supported",
    "documentation_missing",
    "coding_error",
    "ask_provider",
    "payer_policy",
    "other",
)
PURGE_ANCHOR = "    'DELETE FROM note_changes WHERE note_id IN (SELECT id FROM notes WHERE practice_id = $1)',\n"
RETURN_PURGE_STEP = "    'DELETE FROM note_returns WHERE practice_id = $1',\n"
TRIGGERS = ("bodha_append_only", "bodha_stamp", "bodha_no_truncate")


def lane_reason_check(reasons: tuple[str, ...]) -> str:
    allowed = ", ".join(f"'{reason}'" for reason in reasons)
    return f"lane_reason IS NULL OR lane_reason IN ({allowed})"


def purge_with_returns(definition: str) -> str:
    if definition.count(PURGE_ANCHOR) != 1 or RETURN_PURGE_STEP in definition:
        raise RuntimeError(f"{PURGE_FUNCTION} no longer reads as this migration expects")
    return definition.replace(PURGE_ANCHOR, RETURN_PURGE_STEP + PURGE_ANCHOR, 1)


def purge_without_returns(definition: str) -> str:
    if definition.count(RETURN_PURGE_STEP) != 1:
        raise RuntimeError(f"{PURGE_FUNCTION} does not hold the note return step")
    return definition.replace(RETURN_PURGE_STEP, "", 1)


def _run(statement: str) -> None:
    op.get_bind().exec_driver_sql(statement)


def _purge_definition() -> str:
    query = sa.text("SELECT pg_get_functiondef(CAST(:name AS regprocedure))")
    return op.get_bind().scalar(query, {"name": PURGE_FUNCTION})


def _runtime_role_exists() -> bool:
    found = op.get_bind().scalar(sa.text("SELECT 1 FROM pg_roles WHERE rolname = :name"), {"name": RUNTIME_ROLE})
    return bool(found)


def _references() -> list[sa.SchemaItem]:
    targets = (("practice_id", "practices"), ("note_id", "notes"), ("analysis_id", "analyses"), ("actor_id", "users"))
    return [
        sa.ForeignKeyConstraint([column], [f"{target}.id"], name=op.f(f"fk_{TABLE}_{column}_{target}"))
        for column, target in targets
    ]


def _create_returns() -> None:
    allowed = ", ".join(f"'{reason}'" for reason in RETURN_REASONS)
    op.create_table(
        TABLE,
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("clock_timestamp()"), nullable=False
        ),
        sa.Column("practice_id", sa.String(36), nullable=False),
        sa.Column("note_id", sa.String(36), nullable=False),
        sa.Column("analysis_id", sa.String(36), nullable=True),
        sa.Column("actor_id", sa.String(36), nullable=False),
        sa.Column("actor_role", sa.String(16), nullable=True),
        sa.Column("reason", sa.String(24), nullable=False),
        sa.Column("note", sa.String(500), nullable=True),
        sa.Column("flag_reason", sa.Text(), nullable=True),
        sa.Column("finding_keys", JSONB(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f(f"pk_{TABLE}")),
        *_references(),
        sa.CheckConstraint(f"reason IN ({allowed})", name=op.f(f"ck_{TABLE}_reason_allowed")),
        sa.CheckConstraint(
            "reason <> 'other' OR length(btrim(coalesce(note, ''))) > 0", name=op.f(f"ck_{TABLE}_other_noted")
        ),
    )
    op.create_index("ix_note_returns_note", TABLE, ["note_id", "created_at"])


def _row_trigger(name: str, event: str, function: str) -> None:
    _run(f"CREATE TRIGGER {name} BEFORE {event} ON {TABLE} FOR EACH ROW EXECUTE FUNCTION {function}")


def _protect() -> None:
    _row_trigger("bodha_append_only", "UPDATE OR DELETE", "bodha_reject_change()")
    _row_trigger("bodha_stamp", "INSERT", "bodha_stamp('created_at')")
    _run(f"CREATE TRIGGER bodha_no_truncate BEFORE TRUNCATE ON {TABLE} EXECUTE FUNCTION bodha_reject_change()")


def _replace_lane_reason_check(reasons: tuple[str, ...]) -> None:
    op.drop_constraint(op.f(LANE_REASON_CHECK), "notes", type_="check")
    op.create_check_constraint(op.f(LANE_REASON_CHECK), "notes", lane_reason_check(reasons))


def upgrade() -> None:
    _replace_lane_reason_check((*EARLIER_LANE_REASONS, RETURNED))
    op.add_column("notes", sa.Column("returned_at", sa.DateTime(timezone=True), nullable=True))
    _create_returns()
    _protect()
    if _runtime_role_exists():
        _run(f"GRANT SELECT, INSERT ON {TABLE} TO {RUNTIME_ROLE}")
        _run(f"GRANT UPDATE (returned_at) ON notes TO {RUNTIME_ROLE}")
    _run(purge_with_returns(_purge_definition()))


def downgrade() -> None:
    _run(purge_without_returns(_purge_definition()))
    for trigger in TRIGGERS:
        _run(f"DROP TRIGGER {trigger} ON {TABLE}")
    op.drop_index("ix_note_returns_note", table_name=TABLE)
    op.drop_table(TABLE)
    op.execute(f"UPDATE notes SET lane_reason = 'code_changes' WHERE lane_reason = '{RETURNED}'")
    _replace_lane_reason_check(EARLIER_LANE_REASONS)
    op.drop_column("notes", "returned_at")
