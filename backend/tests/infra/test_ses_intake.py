from __future__ import annotations

import importlib.util
import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.services.intake_mail import envelope_message_id, read_envelope

HANDLER_PATH = Path(__file__).resolve().parents[3] / "infra" / "ses_intake" / "handler.py"
BUCKET = "bodha-documents"
MESSAGE_ID = "o3vrnil0e2ic28trm7dfhrc2v0clambda4nbp0g01"
RECIPIENT = "k3j8w2q9x7m4n5p6@intake.example.com"


def _load_handler():
    spec = importlib.util.spec_from_file_location("ses_intake_handler", HANDLER_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


ses_intake = _load_handler()


class FakeS3:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.types: dict[str, str] = {}

    def put_object(self, *, Bucket: str, Key: str, Body: bytes, ContentType: str) -> None:
        assert Bucket == BUCKET
        self.objects[Key], self.types[Key] = Body, ContentType


def _ses(**receipt_changes) -> dict:
    receipt = {
        "timestamp": "2026-11-28T10:15:00.000Z",
        "recipients": [RECIPIENT.upper(), " " + RECIPIENT],
        "spamVerdict": {"status": "PASS"},
        "virusVerdict": {"status": "PASS"},
        "spfVerdict": {"status": "PASS"},
        "dkimVerdict": {"status": "pass"},
        "dmarcVerdict": {"status": "FAIL"},
        "action": {"type": "Lambda", "invocationType": "Event"},
        **receipt_changes,
    }
    mail = {"messageId": MESSAGE_ID, "timestamp": "2026-11-28T10:14:59.000Z", "source": "scans@lakeside.example.com"}
    return {"mail": mail, "receipt": receipt}


def test_the_envelope_carries_the_envelope_recipients_and_every_verdict():
    envelope = ses_intake.envelope_of(_ses())
    assert envelope == {
        "version": 1,
        "message_id": MESSAGE_ID,
        "received_at": "2026-11-28T10:15:00.000Z",
        "recipients": [RECIPIENT],
        "verdicts": {"spam": "PASS", "virus": "PASS", "spf": "PASS", "dkim": "PASS", "dmarc": "FAIL"},
    }


def test_a_missing_verdict_is_recorded_as_blank_rather_than_passed():
    envelope = ses_intake.envelope_of(_ses(virusVerdict=None, dmarcVerdict={"status": None}))
    assert envelope["verdicts"]["virus"] == ""
    assert envelope["verdicts"]["dmarc"] == "NONE"


@pytest.mark.parametrize("message_id", ["", "../practices/x", "a/b", "x" * 129])
def test_a_message_id_that_could_leave_the_prefix_is_refused(message_id):
    event = _ses()
    event["mail"]["messageId"] = message_id
    with pytest.raises(ValueError):
        ses_intake.envelope_of(event)


def test_a_message_without_recipients_is_refused():
    with pytest.raises(ValueError, match="without a recipient"):
        ses_intake.envelope_of(_ses(recipients=[]))


def test_the_handler_writes_one_envelope_beside_the_stored_message_and_logs_no_address(monkeypatch, caplog):
    s3 = FakeS3()
    monkeypatch.setenv("INTAKE_BUCKET", BUCKET)
    monkeypatch.setattr(ses_intake.boto3, "client", lambda name: s3)
    caplog.set_level(logging.INFO, logger="bodha.ses_intake")

    answer = ses_intake.handler({"Records": [{"eventSource": "aws:ses", "ses": _ses()}]}, None)

    key = f"ses-inbound/{MESSAGE_ID}.json"
    assert answer == {"messages": 1}
    assert list(s3.objects) == [key]
    assert s3.types[key] == "application/json"
    logged = " ".join(record.getMessage() for record in caplog.records)
    assert json.loads(logged) == {"event": "ses intake", "message": MESSAGE_ID, "recipients": 1}
    assert "@" not in logged and "lakeside" not in logged


def test_the_worker_reads_what_the_function_writes():
    s3 = FakeS3()
    key = ses_intake.record_envelope(s3, BUCKET, ses_intake.envelope_of(_ses()))
    envelope = read_envelope(s3.objects[key])

    assert envelope_message_id(key) == MESSAGE_ID
    assert envelope.envelope_key == key
    assert envelope.raw_key == f"ses-inbound/{MESSAGE_ID}"
    assert envelope.retained_key == f"ses-retained/{MESSAGE_ID}"
    assert envelope.recipients == (RECIPIENT,)
    assert envelope.received_at == datetime(2026, 11, 28, 10, 15, tzinfo=UTC)
    assert envelope.passed("spam", "virus", "spf", "dkim")
    assert not envelope.passed("dmarc")
