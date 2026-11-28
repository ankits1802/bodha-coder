import importlib.util
from pathlib import Path

import pytest

VERSIONS = Path(__file__).resolve().parents[2] / "alembic" / "versions"


def _load(name: str, file_name: str):
    spec = importlib.util.spec_from_file_location(name, VERSIONS / file_name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _purge_before() -> str:
    return _load("migration_0016", "0016_inbox_views_impact.py").purge_with_work_items()


def test_the_purge_removes_tests_messages_senders_and_addresses_before_batches_and_users():
    body = _load("migration_0021", "0021_email_intake.py").purge_with_intake(_purge_before())
    order = [
        body.index("DELETE FROM intake_tests WHERE practice_id = $1"),
        body.index("DELETE FROM intake_messages WHERE practice_id = $1"),
        body.index("DELETE FROM intake_senders WHERE practice_id = $1"),
        body.index("DELETE FROM intake_addresses WHERE practice_id = $1"),
        body.index("DELETE FROM batches WHERE practice_id = $1"),
        body.index("DELETE FROM users WHERE id = ANY($2)"),
    ]
    assert order == sorted(order)


def test_the_downgrade_takes_back_only_the_email_intake_steps():
    module = _load("migration_0021", "0021_email_intake.py")
    before = _purge_before()
    assert module.purge_without_intake(module.purge_with_intake(before)) == before
    with pytest.raises(RuntimeError):
        module.purge_with_intake(module.purge_with_intake(before))


def test_only_the_message_table_is_append_only_and_every_table_is_guarded():
    module = _load("migration_0021", "0021_email_intake.py")
    assert module.APPEND_ONLY == ("intake_messages",)
    assert set(module.WRITTEN_ONCE) | set(module.APPEND_ONLY) == set(module.NEW_TABLES)
    assert "retired_at" in module.WRITTEN_ONCE["intake_addresses"]
    assert "removed_at" in module.WRITTEN_ONCE["intake_senders"]
