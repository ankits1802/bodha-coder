import importlib.util
from pathlib import Path

VERSIONS = Path(__file__).resolve().parents[2] / "alembic" / "versions"


def _load(name: str, file_name: str):
    spec = importlib.util.spec_from_file_location(name, VERSIONS / file_name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _purge_before() -> str:
    with_work_items = _load("migration_0016", "0016_inbox_views_impact.py").purge_with_work_items()
    return _load("migration_0018", "0018_review_list.py").purge_with_returns(with_work_items)


def test_the_practice_purge_removes_domain_rows_before_the_subscription_and_keeps_organization_admins():
    body = _load("migration_0019", "0019_organizations.py").purge_with_organizations(_purge_before())
    requests = body.index("DELETE FROM domain_join_requests WHERE practice_id = $1")
    claims = body.index("DELETE FROM domain_claims WHERE practice_id = $1")
    assert requests < claims < body.index("DELETE FROM subscriptions WHERE practice_id = $1")
    assert "DELETE FROM note_returns WHERE practice_id = $1" in body
    assert "SELECT 1 FROM organization_memberships AS org_member WHERE org_member.user_id = member.user_id" in body
    assert body.index("organization_memberships AS org_member") < body.index("PERFORM set_config")


def test_the_downgrade_restores_the_practice_purge_unchanged():
    module = _load("migration_0019", "0019_organizations.py")
    before = _purge_before()
    assert module.purge_without_organizations(module.purge_with_organizations(before)) == before


def test_the_organization_purge_never_reaches_practice_records():
    functions = (VERSIONS / "0019_organizations.sql").read_text(encoding="utf-8")
    purge = functions[functions.index("CREATE FUNCTION bodha_purge_organization(") :]
    for table in ("notes", "access_log", "practice_memberships", "signing_events", "practices"):
        assert f"DELETE FROM {table} " not in purge
    assert "SELECT 1 FROM practice_memberships AS place WHERE place.user_id = member.user_id" in purge
