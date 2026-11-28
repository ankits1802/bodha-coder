import importlib.util
from pathlib import Path

import pytest

from app.models import DOCUMENT_OUTCOMES, DOCUMENT_REASONS, EHR_KEY_ALGORITHMS, PULL_OUTCOMES, PULL_REASONS, Base

VERSIONS = Path(__file__).resolve().parents[2] / "alembic" / "versions"


def _load(name: str, file_name: str):
    spec = importlib.util.spec_from_file_location(name, VERSIONS / file_name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _purge_before() -> str:
    work_items = _load("migration_0016", "0016_inbox_views_impact.py").purge_with_work_items()
    return _load("migration_0021", "0021_email_intake.py").purge_with_intake(work_items)


def test_the_purge_removes_documents_runs_connections_and_keys_before_the_notes():
    body = _load("migration_0024", "0024_ehr_connection.py").purge_with_ehr(_purge_before())
    order = [
        body.index("DELETE FROM ehr_documents WHERE practice_id = $1"),
        body.index("DELETE FROM ehr_pull_runs WHERE practice_id = $1"),
        body.index("DELETE FROM ehr_connections WHERE practice_id = $1"),
        body.index("DELETE FROM ehr_keys WHERE practice_id = $1"),
        body.index("'DELETE FROM notes WHERE practice_id = $1'"),
        body.index("DELETE FROM batches WHERE practice_id = $1"),
    ]
    assert order == sorted(order)


def test_the_downgrade_takes_back_only_the_ehr_steps():
    module = _load("migration_0024", "0024_ehr_connection.py")
    before = _purge_before()
    assert module.purge_without_ehr(module.purge_with_ehr(before)) == before
    with pytest.raises(RuntimeError):
        module.purge_with_ehr(module.purge_with_ehr(before))


def test_documents_and_revisions_are_append_only_and_keys_and_runs_are_written_once():
    module = _load("migration_0024", "0024_ehr_connection.py")
    assert module.APPEND_ONLY == ("ehr_connections", "ehr_documents")
    assert set(module.WRITTEN_ONCE) | set(module.APPEND_ONLY) == set(module.NEW_TABLES)
    for table, columns in module.WRITTEN_ONCE.items():
        assert set(columns) == set(Base.metadata.tables[table].columns.keys()), table


def test_the_migration_allows_exactly_the_values_the_models_name():
    module = _load("migration_0024", "0024_ehr_connection.py")
    assert module.PULL_REASONS == PULL_REASONS
    assert module.PULL_OUTCOMES == PULL_OUTCOMES
    assert module.DOCUMENT_REASONS == DOCUMENT_REASONS
    assert module.DOCUMENT_OUTCOMES == DOCUMENT_OUTCOMES
    assert module.KEY_ALGORITHMS == EHR_KEY_ALGORITHMS
    assert module.SOURCES_AFTER == ("upload", "intake", "fhir")
    batches = Base.metadata.tables["batches"]
    [check] = [item for item in batches.constraints if getattr(item, "name", None) == "ck_batches_source_allowed"]
    assert str(check.sqltext) == "source IN ('upload', 'intake', 'fhir')"
