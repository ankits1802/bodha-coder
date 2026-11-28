import importlib.util
from pathlib import Path

import pytest

from app.models import USAGE_COUNTS, USAGE_KINDS, USAGE_OUTCOMES, USAGE_STEPS, USAGE_TASKS
from app.models.accounts import PRACTICE_MEMBER_ROLES

VERSIONS = Path(__file__).resolve().parents[2] / "alembic" / "versions"


def _load(name: str, file_name: str):
    spec = importlib.util.spec_from_file_location(name, VERSIONS / file_name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _purge_before() -> str:
    with_work_items = _load("migration_0016", "0016_inbox_views_impact.py").purge_with_work_items()
    with_returns = _load("migration_0018", "0018_review_list.py").purge_with_returns(with_work_items)
    return _load("migration_0019", "0019_organizations.py").purge_with_organizations(with_returns)


def _migration():
    return _load("migration_0020", "0020_practice_measures_and_usage.py")


def test_the_purge_removes_usage_and_measures_before_the_people_they_point_to():
    body = _migration().purge_with_measures_and_usage(_purge_before())
    usage = body.index("DELETE FROM usage_events WHERE practice_id = $1 OR user_id = ANY($2)")
    measures = body.index("DELETE FROM practice_measures WHERE practice_id = $1")
    assert usage < measures < body.index("DELETE FROM mips_lists WHERE practice_id = $1")
    assert measures < body.index("DELETE FROM users WHERE id = ANY($2)")
    assert "DELETE FROM domain_claims WHERE practice_id = $1" in body


def test_the_downgrade_takes_back_only_the_new_steps():
    module = _migration()
    before = _purge_before()
    assert module.purge_without_measures_and_usage(module.purge_with_measures_and_usage(before)) == before
    with pytest.raises(RuntimeError):
        module.purge_with_measures_and_usage(module.purge_with_measures_and_usage(before))


def test_the_migration_allows_exactly_the_vocabulary_the_models_name():
    module = _migration()
    assert module.PRACTICE_ROLES == PRACTICE_MEMBER_ROLES
    assert (module.KINDS, module.TASKS, module.OUTCOMES, module.STEPS) == (
        USAGE_KINDS,
        USAGE_TASKS,
        USAGE_OUTCOMES,
        USAGE_STEPS,
    )
    assert module.COUNTS == USAGE_COUNTS
