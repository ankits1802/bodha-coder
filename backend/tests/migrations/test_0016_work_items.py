import importlib.util
from pathlib import Path

MIGRATION = Path(__file__).resolve().parents[2] / "alembic" / "versions" / "0016_inbox_views_impact.py"


def migration():
    spec = importlib.util.spec_from_file_location("migration_0016", MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_purge_removes_inbox_items_and_saved_views_before_the_people_who_held_them():
    body = migration().purge_with_work_items()
    inbox = body.index("DELETE FROM inbox_items WHERE practice_id = $1 OR user_id = ANY($2)")
    views = body.index("DELETE FROM queue_views WHERE practice_id = $1 OR user_id = ANY($2)")
    assert body.startswith("CREATE OR REPLACE FUNCTION bodha_purge_practice(")
    assert inbox < views < body.index("DELETE FROM sessions") < body.index("DELETE FROM users WHERE id = ANY($2)")


def test_the_downgrade_restores_the_purge_of_0015_unchanged():
    module = migration()
    previous = module.previous_purge()
    assert "inbox_items" not in previous and "queue_views" not in previous
    assert module.purge_with_work_items().replace("".join(module.WORK_ITEM_STEPS), "") == previous
