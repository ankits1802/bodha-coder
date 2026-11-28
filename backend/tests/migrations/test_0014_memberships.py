import importlib.util
from datetime import UTC, datetime
from pathlib import Path

from app.core.roles import PRACTICE_ROLES
from app.models import AUTH_EVENT_KINDS, MEMBERSHIP_STATUSES

MIGRATION = Path(__file__).resolve().parents[2] / "alembic" / "versions" / "0014_practice_memberships.py"
JOINED = datetime(2026, 3, 2, 9, 30, tzinfo=UTC)


def migration():
    spec = importlib.util.spec_from_file_location("migration_0014", MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def person(**changes) -> dict:
    return {
        "id": "u-1",
        "realm": "practice",
        "practice_id": "p-1",
        "role": "coder",
        "status": "active",
        "created_at": JOINED,
        **changes,
    }


def test_a_practice_user_becomes_one_membership_with_their_practice_role_and_status():
    row = migration().membership_for(person(role="biller", status="invited"))
    assert {key: row[key] for key in row if key != "id"} == {
        "user_id": "u-1",
        "realm": "practice",
        "practice_id": "p-1",
        "role": "biller",
        "status": "invited",
        "invited_by": None,
        "created_at": JOINED,
        "ended_at": None,
    }
    assert len(row["id"]) == 36


def test_a_blocked_practice_user_keeps_the_block_on_the_membership():
    assert migration().membership_for(person(status="blocked"))["status"] == "blocked"


def test_hq_users_and_users_without_a_practice_get_no_membership():
    module = migration()
    assert module.membership_for(person(realm="hq", role="hq", practice_id=None)) is None
    assert module.membership_for(person(practice_id=None)) is None


def test_downgrade_puts_the_one_live_membership_back_on_the_user():
    module = migration()
    membership = {"practice_id": "p-2", "role": "admin", "status": "active", "ended_at": None}
    assert module.legacy_columns(person(role="coder"), membership) == {
        "id": "u-1",
        "practice_id": "p-2",
        "role": "admin",
        "status": "active",
    }


def test_downgrade_blocks_a_user_blocked_in_their_practice_and_detaches_one_who_left():
    module = migration()
    blocked = {"practice_id": "p-1", "role": "coder", "status": "blocked", "ended_at": None}
    assert module.legacy_columns(person(), blocked)["status"] == "blocked"
    left = {"practice_id": "p-1", "role": "coder", "status": "active", "ended_at": JOINED}
    assert module.legacy_columns(person(), left) == {
        "id": "u-1",
        "practice_id": None,
        "role": "coder",
        "status": "active",
    }
    assert module.legacy_columns(person(status="invited"), None)["practice_id"] is None


def test_the_migration_names_the_same_roles_statuses_and_event_kinds_as_the_models():
    module = migration()
    assert module.PRACTICE_MEMBER_ROLES == PRACTICE_ROLES
    assert module.MEMBERSHIP_STATUSES == MEMBERSHIP_STATUSES
    assert AUTH_EVENT_KINDS[: len(module.AUTH_EVENT_KINDS)] == module.AUTH_EVENT_KINDS
    assert module.revision == "0014"
