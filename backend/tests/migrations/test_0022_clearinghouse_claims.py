import importlib.util
from pathlib import Path

import pytest

VERSIONS = Path(__file__).resolve().parents[2] / "alembic" / "versions"
NEW_TABLES = (
    "claim_acks",
    "claim_ack_files",
    "claim_deliveries",
    "claim_submission_items",
    "claim_submissions",
    "claim_details",
    "clearinghouse_connections",
)


def _load(name: str, file_name: str):
    spec = importlib.util.spec_from_file_location(name, VERSIONS / file_name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _purge_before() -> str:
    body = _load("migration_0016", "0016_inbox_views_impact.py").purge_with_work_items()
    signatures = _load("migration_0017", "0017_signatures.py")
    body = body.replace(signatures.PURGE_ANCHOR, signatures.SEALED_PURGE_STEPS + signatures.PURGE_ANCHOR, 1)
    body = _load("migration_0018", "0018_review_list.py").purge_with_returns(body)
    body = _load("migration_0019", "0019_organizations.py").purge_with_organizations(body)
    body = _load("migration_0020", "0020_practice_measures_and_usage.py").purge_with_measures_and_usage(body)
    return _load("migration_0021", "0021_email_intake.py").purge_with_intake(body)


def test_the_purge_removes_claim_records_children_first_before_exports_notes_and_users():
    body = _load("migration_0022", "0022_clearinghouse_claims.py").purge_with_claims(_purge_before())
    order = [body.index(f"DELETE FROM {table} WHERE practice_id = $1") for table in NEW_TABLES]
    later = [
        body.index("DELETE FROM claim_export_items WHERE practice_id = $1"),
        body.index("DELETE FROM approved_claims WHERE practice_id = $1"),
        body.index("DELETE FROM notes WHERE practice_id = $1"),
        body.index("DELETE FROM users WHERE id = ANY($2)"),
    ]
    assert order == sorted(order) and order[-1] < later[0] and later == sorted(later)


def test_the_downgrade_takes_back_only_the_claim_steps_and_a_second_upgrade_is_refused():
    module = _load("migration_0022", "0022_clearinghouse_claims.py")
    before = _purge_before()
    assert module.purge_without_claims(module.purge_with_claims(before)) == before
    with pytest.raises(RuntimeError):
        module.purge_with_claims(module.purge_with_claims(before))


def test_every_new_table_is_guarded_and_only_the_connection_takes_updates():
    module = _load("migration_0022", "0022_clearinghouse_claims.py")
    assert module.revision == "0022" and module.down_revision == "0021"
    assert set(module.NEW_TABLES) == set(NEW_TABLES)
    assert set(module.APPEND_ONLY) == set(NEW_TABLES) - {"clearinghouse_connections"}
    columns = module.written_once_columns()
    assert {"id", "created_at", "practice_id", "secret", "host_key_sha256", "retired_at", "retired_by"} <= set(columns)
    assert len(columns) == len(set(columns)) == 22
    assert "claim_rejected" not in module.INBOX_KINDS and module.REJECTION_KIND == "claim_rejected"
