from __future__ import annotations

import json
import logging
from collections.abc import Iterator

import pytest
import sentry_sdk
from sentry_sdk.transport import Transport

from app.core.config import Settings
from app.core.error_reports import REDACTED, error_report_options, scrub_breadcrumb, scrub_event, start_error_reports

DSN = "https://0123456789abcdef0123456789abcdef@o1.ingest.us.sentry.io/2"
PATIENT = "REYES MARISOL 1959-03-02"


def _settings(**changes) -> Settings:
    values = {"secret_key": "s" * 40, "s3_bucket": "documents", "app_version": "2026.11.28-4f2a9c1", **changes}
    return Settings(**values)


class CapturedEnvelopes(Transport):
    def __init__(self) -> None:
        super().__init__()
        self.events: list[dict] = []

    def capture_envelope(self, envelope) -> None:
        event = envelope.get_event()
        if event is not None:
            self.events.append(event)


@pytest.fixture
def captured() -> Iterator[CapturedEnvelopes]:
    transport = CapturedEnvelopes()
    sentry_sdk.init(**error_report_options(_settings(sentry_dsn=DSN), process="worker"), transport=transport)
    yield transport
    sentry_sdk.get_client().close()
    sentry_sdk.get_global_scope().set_client(None)


def test_error_reports_stay_off_without_a_dsn():
    assert start_error_reports(_settings(), process="api") is False
    assert not sentry_sdk.get_client().is_active()


def test_a_dsn_that_is_not_a_sentry_address_is_refused_without_being_echoed():
    with pytest.raises(ValueError) as refused:
        _settings(sentry_dsn="http://key@sentry.example.com/1?secret=yes")
    assert "secret=yes" not in str(refused.value)


KEPT_FRAME = {
    "filename": "app/services/uploads.py",
    "module": "app.services.uploads",
    "function": "_add_note",
    "lineno": 210,
    "in_app": True,
}
FRAME = {
    **KEPT_FRAME,
    "abs_path": "/app/.venv/lib/python3.14/site-packages/app/services/uploads.py",
    "context_line": f"    name = '{PATIENT}'",
    "pre_context": ["x"],
    "vars": {"file": PATIENT},
}


def _exception(value: str, frame: dict) -> dict:
    return {"type": "Invalid", "module": "app.core.errors", "value": value, "stacktrace": {"frames": [frame]}}


def test_an_exception_keeps_its_type_and_frames_and_loses_its_message_and_values():
    event = {
        "event_id": "e1",
        "level": "error",
        "release": "2026.11.28-4f2a9c1",
        "exception": {"values": [_exception(PATIENT, FRAME)]},
        "request": {"url": f"https://www.bodhaai.co/api/notes?q={PATIENT}", "data": PATIENT, "cookies": "s=1"},
        "user": {"email": "coder@lakeside.example.com", "ip_address": "203.0.113.9"},
        "extra": {"name": PATIENT},
        "tags": {"process": "api", "patient": PATIENT},
        "breadcrumbs": {"values": [{"category": "query", "message": PATIENT, "data": {"q": PATIENT}, "level": "info"}]},
        "contexts": {"runtime": {"name": "CPython", "version": "3.14.0", "raw_description": PATIENT}},
    }

    assert scrub_event(event) == {
        "event_id": "e1",
        "level": "error",
        "release": "2026.11.28-4f2a9c1",
        "exception": {"values": [_exception(REDACTED, KEPT_FRAME)]},
        "tags": {"process": "api"},
        "breadcrumbs": {"values": [{"category": "query", "level": "info"}]},
        "contexts": {"runtime": {"name": "CPython", "version": "3.14.0"}},
    }


def test_a_log_template_is_kept_only_when_it_is_known_to_be_safe():
    known = scrub_event({"logentry": {"message": "%s failed", "params": [PATIENT], "formatted": f"{PATIENT} failed"}})
    unknown = scrub_event({"logentry": {"message": f"could not read {PATIENT}"}})
    assert known == {"logentry": {"message": "%s failed"}}
    assert unknown == {"logentry": {"message": REDACTED}}


def test_a_breadcrumb_keeps_no_text():
    crumb = {"type": "http", "category": "httplib", "message": PATIENT, "data": {"url.full": PATIENT}, "level": "info"}
    assert scrub_breadcrumb(crumb, None) == {"type": "http", "category": "httplib", "level": "info"}


def test_a_logged_error_reaches_sentry_with_the_release_and_without_patient_data(captured):
    try:
        raise ValueError(f"no provider for {PATIENT}")
    except ValueError:
        logging.getLogger("bodha.worker").exception("%s failed", PATIENT)

    [event] = captured.events
    assert event["release"] == "2026.11.28-4f2a9c1"
    assert event["exception"]["values"][0]["type"] == "ValueError"
    assert event["exception"]["values"][0]["value"] == REDACTED
    assert event["logentry"] == {"message": "%s failed"}
    assert "REYES" not in json.dumps(event, default=str)
