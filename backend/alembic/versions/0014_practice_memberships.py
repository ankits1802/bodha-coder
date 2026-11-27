from collections.abc import Iterable, Mapping
from typing import Any
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None

PRACTICE_REALM = "practice"
BLOCKED = "blocked"
PRACTICE_MEMBER_ROLES = ("admin", "coder", "cdi", "compliance", "biller", "viewer")
MEMBERSHIP_STATUSES = ("invited", "active", "blocked")
AUTH_EVENT_KINDS = (
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
LEGACY_FUNCTION = "legacy_user_membership"
LEGACY_TRIGGER = "users_legacy_membership"
CREATE_LEGACY_FUNCTION = f"""
CREATE FUNCTION {LEGACY_FUNCTION}() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.practice_id IS NULL OR NEW.realm <> '{PRACTICE_REALM}' THEN
        RETURN NEW;
    END IF;
    INSERT INTO practice_memberships (id, user_id, realm, practice_id, role, status, created_at)
    VALUES (gen_random_uuid()::text, NEW.id, '{PRACTICE_REALM}', NEW.practice_id, NEW.role, NEW.status, now())
    ON CONFLICT (user_id, practice_id) DO UPDATE SET role = EXCLUDED.role, status = EXCLUDED.status
    WHERE practice_memberships.ended_at IS NULL;
    RETURN NEW;
END
$$
"""
CREATE_LEGACY_TRIGGER = (
    f"CREATE TRIGGER {LEGACY_TRIGGER} AFTER INSERT OR UPDATE OF practice_id, role, status ON users "
    f"FOR EACH ROW EXECUTE FUNCTION {LEGACY_FUNCTION}()"
)
MEMBERSHIPS_LIVE_LAST = (
    "SELECT user_id, practice_id, role, status, ended_at FROM practice_memberships ORDER BY ended_at NULLS LAST"
)
PEOPLE_IN_SEVERAL = (
    "SELECT count(*) FROM (SELECT user_id FROM practice_memberships WHERE ended_at IS NULL "
    "GROUP BY user_id HAVING count(*) > 1) AS several"
)


def membership_for(person: Mapping[str, Any]) -> dict[str, Any] | None:
    if person["realm"] != PRACTICE_REALM or person["practice_id"] is None:
        return None
    return {
        "id": str(uuid4()),
        "user_id": person["id"],
        "realm": PRACTICE_REALM,
        "practice_id": person["practice_id"],
        "role": person["role"],
        "status": person["status"],
        "invited_by": None,
        "created_at": person["created_at"],
        "ended_at": None,
    }


def legacy_columns(person: Mapping[str, Any], membership: Mapping[str, Any] | None) -> dict[str, Any]:
    if membership is None or membership["ended_at"] is not None:
        return {"id": person["id"], "practice_id": None, "role": person["role"], "status": person["status"]}
    blocked = BLOCKED in (membership["status"], person["status"])
    return {
        "id": person["id"],
        "practice_id": membership["practice_id"],
        "role": membership["role"],
        "status": BLOCKED if blocked else person["status"],
    }


def upgrade() -> None:
    _create_memberships()
    _create_auth_events()
    op.add_column("users", sa.Column("last_practice_id", sa.String(36), nullable=True))
    op.create_foreign_key(
        op.f("fk_users_last_practice_id_practices"), "users", "practices", ["last_practice_id"], ["id"]
    )
    op.add_column("sessions", sa.Column("practice_id", sa.String(36), nullable=True))
    op.create_foreign_key(op.f("fk_sessions_practice_id_practices"), "sessions", "practices", ["practice_id"], ["id"])
    op.create_index(op.f("ix_sessions_practice_id"), "sessions", ["practice_id"])
    _copy_memberships(op.get_bind())
    op.execute(CREATE_LEGACY_FUNCTION)
    op.execute(CREATE_LEGACY_TRIGGER)


def downgrade() -> None:
    bind = op.get_bind()
    several = bind.scalar(sa.text(PEOPLE_IN_SEVERAL))
    if several:
        raise RuntimeError(f"{several} people belong to more than one practice; the earlier schema holds one")
    op.execute(f"DROP TRIGGER {LEGACY_TRIGGER} ON users")
    op.execute(f"DROP FUNCTION {LEGACY_FUNCTION}()")
    _restore_legacy_columns(bind)
    op.drop_index(op.f("ix_sessions_practice_id"), table_name="sessions")
    op.drop_constraint(op.f("fk_sessions_practice_id_practices"), "sessions", type_="foreignkey")
    op.drop_column("sessions", "practice_id")
    op.drop_constraint(op.f("fk_users_last_practice_id_practices"), "users", type_="foreignkey")
    op.drop_column("users", "last_practice_id")
    op.drop_table("auth_events")
    op.drop_table("practice_memberships")


def _create_memberships() -> None:
    op.create_table(
        "practice_memberships",
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("realm", sa.String(16), server_default=sa.text(f"'{PRACTICE_REALM}'"), nullable=False),
        sa.Column("practice_id", sa.String(36), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("invited_by", sa.String(36), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(f"realm = '{PRACTICE_REALM}'", name=op.f("ck_practice_memberships_realm_practice")),
        sa.CheckConstraint(_one_of("role", PRACTICE_MEMBER_ROLES), name=op.f("ck_practice_memberships_role_allowed")),
        sa.CheckConstraint(_one_of("status", MEMBERSHIP_STATUSES), name=op.f("ck_practice_memberships_status_allowed")),
        sa.ForeignKeyConstraint(
            ["user_id", "realm"], ["users.id", "users.realm"], name=op.f("fk_practice_memberships_user_id_users")
        ),
        sa.ForeignKeyConstraint(
            ["practice_id"], ["practices.id"], name=op.f("fk_practice_memberships_practice_id_practices")
        ),
        sa.ForeignKeyConstraint(
            ["invited_by"],
            ["users.id"],
            name=op.f("fk_practice_memberships_invited_by_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_practice_memberships")),
        sa.UniqueConstraint("user_id", "practice_id", name=op.f("uq_practice_memberships_user_id")),
    )
    op.create_index("ix_practice_memberships_practice_role", "practice_memberships", ["practice_id", "role", "status"])


def _create_auth_events() -> None:
    op.create_table(
        "auth_events",
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("realm", sa.String(16), nullable=True),
        sa.Column("user_id", sa.String(36), nullable=True),
        sa.Column("practice_id", sa.String(36), nullable=True),
        sa.Column("email_hash", sa.String(64), nullable=True),
        sa.Column("detail", sa.String(200), nullable=True),
        sa.Column("ip", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.String(300), nullable=True),
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(_one_of("kind", AUTH_EVENT_KINDS), name=op.f("ck_auth_events_kind_allowed")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_auth_events")),
    )
    op.create_index("ix_auth_events_user_time", "auth_events", ["user_id", "created_at"])
    op.create_index("ix_auth_events_practice_time", "auth_events", ["practice_id", "created_at"])


def _copy_memberships(bind: sa.Connection) -> None:
    people = bind.execute(sa.text("SELECT id, realm, practice_id, role, status, created_at FROM users")).mappings()
    rows = _memberships(people)
    if rows:
        op.bulk_insert(_memberships_table(), rows)
    op.execute("UPDATE users SET last_practice_id = practice_id WHERE realm = 'practice' AND practice_id IS NOT NULL")


def _memberships(people: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in (membership_for(person) for person in people) if row is not None]


def _restore_legacy_columns(bind: sa.Connection) -> None:
    memberships = {row["user_id"]: row for row in bind.execute(sa.text(MEMBERSHIPS_LIVE_LAST)).mappings()}
    people = bind.execute(sa.text("SELECT id, role, status FROM users WHERE realm = 'practice'")).mappings().all()
    values = [legacy_columns(person, memberships.get(person["id"])) for person in people]
    if values:
        bind.execute(
            sa.text("UPDATE users SET practice_id = :practice_id, role = :role, status = :status WHERE id = :id"),
            values,
        )


def _memberships_table() -> sa.Table:
    return sa.table(
        "practice_memberships",
        sa.column("id", sa.String),
        sa.column("user_id", sa.String),
        sa.column("realm", sa.String),
        sa.column("practice_id", sa.String),
        sa.column("role", sa.String),
        sa.column("status", sa.String),
        sa.column("invited_by", sa.String),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("ended_at", sa.DateTime(timezone=True)),
    )


def _one_of(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in values)})"
