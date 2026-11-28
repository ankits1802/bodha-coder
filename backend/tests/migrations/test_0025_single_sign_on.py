import importlib.util
from pathlib import Path

import pytest

from app.models import AUTH_EVENT_KINDS, SSO_NEW_PERSON_ROLES

VERSIONS = Path(__file__).resolve().parents[2] / "alembic" / "versions"
ORGANIZATION_HEAD = "CREATE FUNCTION bodha_purge_organization("


def _load(name: str, file_name: str):
    spec = importlib.util.spec_from_file_location(name, VERSIONS / file_name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _practice_purge() -> str:
    before = _load("migration_0016", "0016_inbox_views_impact.py").purge_with_work_items()
    return _load("migration_0019", "0019_organizations.py").purge_with_organizations(before)


def _organization_purge() -> str:
    statements = (VERSIONS / "0019_organizations.sql").read_text(encoding="utf-8").split("\n;\n")
    [found] = [statement for statement in statements if statement.strip().startswith(ORGANIZATION_HEAD)]
    return found


def _migration():
    return _load("migration_0025", "0025_single_sign_on.py")


def test_the_practice_purge_removes_single_sign_on_before_domains_and_people():
    module = _migration()
    body = module.with_steps(_practice_purge(), module.PRACTICE_ANCHOR, module.PRACTICE_STEPS, "practice")
    order = [
        body.index(
            "DELETE FROM sso_assertions WHERE connection_id IN (SELECT id FROM sso_connections WHERE practice_id = $1)"
        ),
        body.index(
            "DELETE FROM sso_versions WHERE connection_id IN (SELECT id FROM sso_connections WHERE practice_id = $1)"
        ),
        body.index("DELETE FROM sso_connections WHERE practice_id = $1"),
        body.index("DELETE FROM domain_join_requests WHERE practice_id = $1"),
        body.index("DELETE FROM users WHERE id = ANY($2)"),
    ]
    assert order == sorted(order)


def test_the_organization_purge_removes_single_sign_on_before_its_claims_and_people():
    module = _migration()
    body = module.with_steps(
        _organization_purge(), module.ORGANIZATION_ANCHOR, module.ORGANIZATION_STEPS, "organization"
    )
    order = [
        body.index(
            "DELETE FROM sso_assertions WHERE connection_id IN "
            "(SELECT id FROM sso_connections WHERE organization_id = $1)"
        ),
        body.index("DELETE FROM sso_connections WHERE organization_id = $1"),
        body.index("DELETE FROM domain_claims WHERE organization_id = $1"),
        body.index("DELETE FROM users WHERE id = ANY($2)"),
    ]
    assert order == sorted(order)


def test_the_downgrade_takes_back_only_the_single_sign_on_steps():
    module = _migration()
    for before, anchor, steps in (
        (_practice_purge(), module.PRACTICE_ANCHOR, module.PRACTICE_STEPS),
        (_organization_purge(), module.ORGANIZATION_ANCHOR, module.ORGANIZATION_STEPS),
    ):
        patched = module.with_steps(before, anchor, steps, "purge")
        assert module.without_steps(patched, steps, "purge") == before
        with pytest.raises(RuntimeError):
            module.with_steps(patched, anchor, steps, "purge")


def test_the_migration_names_the_same_event_kinds_and_roles_as_the_models():
    module = _migration()
    assert module.AUTH_EVENT_KINDS == AUTH_EVENT_KINDS
    assert module.NEW_PERSON_ROLES == SSO_NEW_PERSON_ROLES
    assert (module.revision, module.down_revision) == ("0025", "0024")
    assert set(module.APPEND_ONLY) | {module.CONNECTIONS} == set(module.NEW_TABLES)
    assert "removed_at" in module.CONNECTION_COLUMNS and "removed_by" in module.CONNECTION_COLUMNS
