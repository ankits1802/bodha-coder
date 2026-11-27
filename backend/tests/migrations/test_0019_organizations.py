import importlib.util
from pathlib import Path

VERSIONS = Path(__file__).resolve().parents[2] / "alembic" / "versions"
MIGRATION = VERSIONS / "0019_organizations.py"
PRACTICE_PURGE = VERSIONS / "0015_audit_hardening.sql"
PURGE_HEAD = "CREATE FUNCTION bodha_purge_practice("


def migration():
    spec = importlib.util.spec_from_file_location("migration_0019", MIGRATION)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def practice_purge() -> str:
    statements = PRACTICE_PURGE.read_text(encoding="utf-8").split("\n;\n")
    return next(statement for statement in statements if statement.strip().startswith(PURGE_HEAD))


def test_the_practice_purge_removes_domain_rows_before_the_subscription_and_keeps_organization_admins():
    body = migration().purge_with_organizations(practice_purge())
    requests = body.index("DELETE FROM domain_join_requests WHERE practice_id = $1")
    claims = body.index("DELETE FROM domain_claims WHERE practice_id = $1")
    assert requests < claims < body.index("DELETE FROM subscriptions WHERE practice_id = $1")
    assert "SELECT 1 FROM organization_memberships AS org_member WHERE org_member.user_id = member.user_id" in body
    assert body.index("organization_memberships AS org_member") < body.index("PERFORM set_config")


def test_the_downgrade_restores_the_practice_purge_unchanged():
    module = migration()
    original = practice_purge()
    assert module.purge_without_organizations(module.purge_with_organizations(original)) == original


def test_the_organization_purge_never_reaches_practice_records():
    functions = (VERSIONS / "0019_organizations.sql").read_text(encoding="utf-8")
    purge = functions[functions.index("CREATE FUNCTION bodha_purge_organization(") :]
    for table in ("notes", "access_log", "practice_memberships", "signing_events", "practices"):
        assert f"DELETE FROM {table} " not in purge
    assert "SELECT 1 FROM practice_memberships AS place WHERE place.user_id = member.user_id" in purge
