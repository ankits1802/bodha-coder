from __future__ import annotations

import asyncio
import json
import logging
import sys
from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime
from typing import Any

import boto3
import pytest
from botocore.stub import Stubber

from app.adapters import object_store
from app.api.routes import health
from app.core.config import get_settings
from app.core.db import get_session
from app.core.logging import ACCESS_LOGGER, JsonFormatter, log_queue_metrics
from app.main import app

UUID_HEX_LENGTH = 32
SAFE_REQUEST_ID = "0f1e2d3c-4b5a-6978-8796-a5b4c3d2e1f0"


class AnsweringBucket:
    async def check_bucket(self) -> None:
        return None


class FailingBucket:
    async def check_bucket(self) -> None:
        raise OSError("connection refused")


class HangingBucket:
    async def check_bucket(self) -> None:
        await asyncio.sleep(5)


class FailingSession:
    async def execute(self, statement: Any) -> None:
        raise OSError("connection refused")


async def failing_session() -> AsyncIterator[FailingSession]:
    yield FailingSession()


@pytest.fixture
def database_down() -> Iterator[None]:
    app.dependency_overrides[get_session] = failing_session
    yield
    app.dependency_overrides.pop(get_session)


def access_lines(caplog: pytest.LogCaptureFixture) -> list[dict[str, Any]]:
    formatter = JsonFormatter()
    return [json.loads(formatter.format(record)) for record in caplog.records if record.name == ACCESS_LOGGER]


async def test_liveness_answers_ok(harness):
    response = await harness.client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_ready_when_the_database_and_the_bucket_answer(harness):
    app.state.store = AnsweringBucket()
    response = await harness.client.get("/api/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "checks": {"database": "ok", "storage": "ok"}}


async def test_not_ready_when_the_bucket_check_fails(harness):
    app.state.store = FailingBucket()
    response = await harness.client.get("/api/health/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "not ready", "checks": {"database": "ok", "storage": "unavailable"}}


async def test_not_ready_when_the_bucket_does_not_answer_in_time(harness, monkeypatch):
    monkeypatch.setattr(health, "READY_TIMEOUT_SECONDS", 0.05)
    app.state.store = HangingBucket()
    response = await harness.client.get("/api/health/ready")
    assert response.status_code == 503
    assert response.json()["checks"] == {"database": "ok", "storage": "unavailable"}


async def test_not_ready_when_the_database_fails(harness, database_down):
    app.state.store = AnsweringBucket()
    response = await harness.client.get("/api/health/ready")
    assert response.status_code == 503
    assert response.json()["checks"] == {"database": "unavailable", "storage": "ok"}


async def test_the_store_checks_its_bucket_with_one_head_request(monkeypatch):
    client = boto3.client("s3", region_name="us-east-1", aws_access_key_id="test", aws_secret_access_key="test")
    monkeypatch.setattr(object_store.boto3, "client", lambda *args, **kwargs: client)
    store = object_store.S3ObjectStore(get_settings())
    with Stubber(client) as stubber:
        stubber.add_response("head_bucket", {}, {"Bucket": get_settings().s3_bucket})
        await store.check_bucket()
        stubber.assert_no_pending_responses()


async def test_a_request_line_names_the_route_template_and_never_the_path_or_query(harness, caplog):
    caplog.set_level(logging.INFO, logger=ACCESS_LOGGER)
    await harness.client.get("/api/notes/note-4821", params={"search": "REYES MARISOL"})
    [line] = access_lines(caplog)
    assert {key: line[key] for key in ("logger", "method", "route", "status")} == {
        "logger": ACCESS_LOGGER,
        "method": "GET",
        "route": "/api/notes/{note_id}",
        "status": 401,
    }
    assert isinstance(line["duration_ms"], float)
    text = json.dumps(line)
    assert "REYES" not in text and "note-4821" not in text and "search" not in text


async def test_an_unmatched_path_is_logged_as_unmatched(harness, caplog):
    caplog.set_level(logging.INFO, logger=ACCESS_LOGGER)
    response = await harness.client.get("/api/patients/REYES-MARISOL")
    [line] = access_lines(caplog)
    assert response.status_code == 404
    assert line["route"] == "unmatched"
    assert "REYES" not in json.dumps(line)


async def test_a_safe_request_id_is_echoed_and_logged(harness, caplog):
    caplog.set_level(logging.INFO, logger=ACCESS_LOGGER)
    response = await harness.client.get("/api/health", headers={"X-Request-ID": SAFE_REQUEST_ID})
    [line] = access_lines(caplog)
    assert response.headers["X-Request-ID"] == SAFE_REQUEST_ID
    assert line["request_id"] == SAFE_REQUEST_ID


async def test_an_unsafe_request_id_is_replaced_with_a_new_one(harness, caplog):
    caplog.set_level(logging.INFO, logger=ACCESS_LOGGER)
    response = await harness.client.get("/api/health", headers={"X-Request-ID": "Marisol Reyes 1960-02-11"})
    [line] = access_lines(caplog)
    issued = response.headers["X-Request-ID"]
    assert len(issued) == UUID_HEX_LENGTH and all(character in "0123456789abcdef" for character in issued)
    assert line["request_id"] == issued
    assert "Marisol" not in json.dumps(line)


def test_an_error_is_logged_by_type_and_place_without_its_message():
    try:
        try:
            raise KeyError("REYES MARISOL")
        except KeyError as cause:
            raise ValueError("2026-11-25 - REYES MARISOL - 99215 - Progress.pdf is not a PDF") from cause
    except ValueError:
        record = logging.LogRecord("bodha.worker", logging.ERROR, __file__, 1, "analysis failed", None, None)
        record.exc_info = sys.exc_info()
    line = JsonFormatter().format(record)
    entry = json.loads(line)
    assert entry["message"] == "analysis failed"
    assert entry["error"]["type"] == "builtins.ValueError"
    assert entry["error"]["causes"] == ["builtins.KeyError"]
    assert entry["error"]["frames"][-1].endswith("test_an_error_is_logged_by_type_and_place_without_its_message")
    assert "REYES" not in line and "Progress.pdf" not in line


def test_queue_metrics_are_one_embedded_metric_format_line(caplog):
    logger = logging.getLogger("bodha.worker")
    caplog.set_level(logging.INFO, logger="bodha.worker")
    log_queue_metrics(logger, queued=42, running=7, at=datetime(2026, 11, 27, 14, 30, tzinfo=UTC))
    [record] = [record for record in caplog.records if record.name == "bodha.worker"]
    entry = json.loads(JsonFormatter().format(record))
    assert entry["_aws"] == {
        "Timestamp": 1795789800000,
        "CloudWatchMetrics": [
            {
                "Namespace": "BodhaCoder",
                "Dimensions": [[]],
                "Metrics": [{"Name": "QueuedAnalyses", "Unit": "Count"}, {"Name": "RunningAnalyses", "Unit": "Count"}],
            }
        ],
    }
    assert (entry["QueuedAnalyses"], entry["RunningAnalyses"]) == (42, 7)


def test_queue_metrics_refuse_a_time_without_a_zone():
    with pytest.raises(ValueError, match="timezone-aware"):
        log_queue_metrics(logging.getLogger("bodha.worker"), queued=1, running=0, at=datetime(2026, 11, 27, 14, 30))
