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


def test_the_purge_removes_note_returns_before_the_note_changes_and_the_notes():
    body = _load("migration_0018", "0018_review_list.py").purge_with_returns(_purge_before())
    returns = body.index("DELETE FROM note_returns WHERE practice_id = $1")
    assert returns < body.index("DELETE FROM note_changes") < body.index("DELETE FROM notes WHERE practice_id = $1")


def test_the_downgrade_takes_back_only_the_note_return_step():
    module = _load("migration_0018", "0018_review_list.py")
    before = _purge_before()
    assert module.purge_without_returns(module.purge_with_returns(before)) == before
    with pytest.raises(RuntimeError):
        module.purge_with_returns(module.purge_with_returns(before))


def test_the_lane_reason_check_allows_returned_only_after_the_upgrade():
    module = _load("migration_0018", "0018_review_list.py")
    assert "'returned'" in module.lane_reason_check((*module.EARLIER_LANE_REASONS, module.RETURNED))
    assert "'returned'" not in module.lane_reason_check(module.EARLIER_LANE_REASONS)
