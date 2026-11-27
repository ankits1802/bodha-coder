from __future__ import annotations

import base64
import hashlib
import importlib.util
import io
import json
import logging
import sys
from datetime import date
from pathlib import Path

import pytest

HANDLER_PATH = Path(__file__).resolve().parents[3] / "infra" / "ses_intake" / "handler.py"
BUCKET = "bodha-documents"
PRACTICE = "3f1c2a9e-5b7d-4c11-9e2a-000000000001"
SENDER = "scans@lakeside.example.com"
RECIPIENT = "lakeside-varga"
RAW_KEY = f"ses-inbound/{RECIPIENT}/0123456789abcdefghij"
NOTE_PDF = b"%PDF-1.7\n1 0 obj << /Type /Catalog >> endobj\ntrailer << /Root 1 0 R >>\n%%EOF\n"
SECOND_PDF = b"%PDF-1.4\n% second visit\n%%EOF\n"
NOT_A_PDF = b"PK\x03\x04 a word file"
NOTE_NAME = "2026-11-20 - REYES MARISOL - 99214.pdf"
WORD_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
PASSED = ("X-SES-Spam-Verdict: PASS", "X-SES-Virus-Verdict: PASS")
ADDRESSES = {RECIPIENT: {"practice": PRACTICE, "folder": "varga", "senders": [SENDER.upper()]}}


def _load_handler():
    spec = importlib.util.spec_from_file_location("ses_intake_handler", HANDLER_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


ses_intake = _load_handler()


class FakeS3:
    def __init__(self, raw: bytes, key: str = RAW_KEY) -> None:
        self.objects: dict[str, bytes] = {key: raw}
        self.types: dict[str, str] = {}

    def get_object(self, *, Bucket: str, Key: str) -> dict:
        assert Bucket == BUCKET
        return {"Body": io.BytesIO(self.objects[Key])}

    def put_object(self, *, Bucket: str, Key: str, Body: bytes, ContentType: str) -> None:
        assert Bucket == BUCKET
        self.objects[Key], self.types[Key] = Body, ContentType

    def delete_object(self, *, Bucket: str, Key: str) -> None:
        assert Bucket == BUCKET
        del self.objects[Key]


def _part(headers: list[str], body: str) -> str:
    return "\r\n".join(headers) + "\r\n\r\n" + body + "\r\n"


def _attachment(content_type: str, name: str, data: bytes) -> str:
    headers = [
        f'Content-Type: {content_type}; name="{name}"',
        f'Content-Disposition: attachment; filename="{name}"',
        "Content-Transfer-Encoding: base64",
    ]
    return _part(headers, base64.b64encode(data).decode("ascii"))


def raw_message(
    *,
    sender: str = SENDER,
    subject: str = "Visit notes 2026-11-20",
    verdicts: tuple[str, ...] = PASSED,
) -> bytes:
    head = [
        *verdicts,
        f"From: Front Desk <{sender}>",
        f"To: {RECIPIENT}@intake.example.com",
        f"Subject: {subject}",
        "MIME-Version: 1.0",
        'Content-Type: multipart/mixed; boundary="part-boundary"',
    ]
    parts = [
        _part(["Content-Type: text/plain; charset=utf-8"], "Two visit notes attached."),
        _attachment("application/pdf", NOTE_NAME, NOTE_PDF),
        _attachment(WORD_TYPE, "letter.docx", NOT_A_PDF),
        _attachment("application/octet-stream", "second.PDF", SECOND_PDF),
        _attachment("application/pdf", "broken.pdf", NOT_A_PDF),
    ]
    body = "".join(f"--part-boundary\r\n{part}" for part in parts) + "--part-boundary--\r\n"
    return ("\r\n".join(head) + "\r\n\r\n" + body).encode("utf-8")


def _event(key: str = RAW_KEY) -> dict:
    return {"Records": [{"s3": {"bucket": {"name": BUCKET}, "object": {"key": key}}}]}


def _inbox_key(data: bytes) -> str:
    return f"practices/{PRACTICE}/inbox/varga/2026-11-20/{hashlib.sha256(data).hexdigest()}.pdf"


def _run(raw: bytes) -> tuple[FakeS3, list]:
    s3 = FakeS3(raw)
    outcomes = ses_intake.process_event(s3, ses_intake.load_inboxes(json.dumps(ADDRESSES)), _event())
    return s3, outcomes


def test_each_pdf_attachment_is_written_to_the_practice_inbox_and_the_message_deleted():
    s3, outcomes = _run(raw_message())

    assert s3.objects == {_inbox_key(NOTE_PDF): NOTE_PDF, _inbox_key(SECOND_PDF): SECOND_PDF}
    assert set(s3.types.values()) == {"application/pdf"}
    assert [(outcome.result, outcome.practice, outcome.written) for outcome in outcomes] == [("delivered", PRACTICE, 2)]


def test_the_lambda_entry_point_reads_the_mapping_from_the_environment(monkeypatch):
    s3 = FakeS3(raw_message())
    monkeypatch.setenv("INTAKE_ADDRESSES", json.dumps(ADDRESSES))
    monkeypatch.setattr(ses_intake.boto3, "client", lambda service: s3)

    assert ses_intake.handler(_event(), None) == {"messages": 1, "written": 2}
    assert RAW_KEY not in s3.objects


@pytest.mark.parametrize(
    ("raw", "result"),
    [
        (raw_message(sender="someone@elsewhere.example.com"), "sender_refused"),
        (raw_message(verdicts=("X-SES-Spam-Verdict: PASS", "X-SES-Virus-Verdict: FAIL")), "verdict_failed"),
        (raw_message(verdicts=("X-SES-Virus-Verdict: PASS",)), "verdict_failed"),
        (raw_message(verdicts=(*PASSED, "X-SES-Virus-Verdict: FAIL")), "verdict_failed"),
        (raw_message(subject="Visit notes"), "no_date"),
        (raw_message(subject="Visit notes 2026-02-30"), "no_date"),
    ],
)
def test_a_refused_message_writes_nothing_and_is_deleted(raw, result):
    s3, outcomes = _run(raw)

    assert s3.objects == {}
    assert [(outcome.result, outcome.written) for outcome in outcomes] == [(result, 0)]


def test_an_unknown_recipient_writes_nothing_and_the_message_is_deleted():
    s3 = FakeS3(raw_message(), key="ses-inbound/someone-else/0123456789abcdefghij")
    outcomes = ses_intake.process_event(
        s3, ses_intake.load_inboxes(json.dumps(ADDRESSES)), _event("ses-inbound/someone-else/0123456789abcdefghij")
    )

    assert s3.objects == {}
    assert [(outcome.result, outcome.practice) for outcome in outcomes] == [("unknown_recipient", None)]


def test_the_log_names_the_outcome_but_never_an_address_a_name_or_a_subject(caplog):
    caplog.set_level(logging.INFO, logger="bodha.ses_intake")
    _run(raw_message())
    _run(raw_message(sender="someone@elsewhere.example.com"))

    logged = caplog.text
    assert '"result": "delivered"' in logged and '"result": "sender_refused"' in logged
    for private in (SENDER, "someone@elsewhere.example.com", "REYES", "MARISOL", "Visit notes", RECIPIENT):
        assert private not in logged


def test_a_message_key_outside_the_recipient_folders_is_refused():
    with pytest.raises(ValueError):
        ses_intake.recipient_of("practices/p-1/inbox/varga/2026-11-20/a.pdf")
    with pytest.raises(ValueError):
        ses_intake.recipient_of("ses-inbound/message-without-recipient")
    assert ses_intake.recipient_of("ses-inbound/Lakeside-Varga/abc") == "lakeside-varga"


def test_the_subject_date_is_the_date_of_service():
    assert ses_intake.service_day("Fwd: notes for 2026-11-20 (Dr Varga)") == date(2026, 11, 20)
    assert ses_intake.service_day("Ref 120261120999") is None


@pytest.mark.parametrize(
    "inbox",
    [
        {"practice": PRACTICE, "folder": "processed", "senders": [SENDER]},
        {"practice": PRACTICE, "folder": "varga", "senders": []},
        {"practice": PRACTICE, "folder": "varga", "senders": [SENDER], "inbox": "notes"},
        {"practice": "practices/other", "folder": "varga", "senders": [SENDER]},
        {"folder": "varga", "senders": [SENDER]},
    ],
)
def test_a_malformed_mapping_stops_the_function(inbox):
    with pytest.raises(ValueError):
        ses_intake.load_inboxes(json.dumps({RECIPIENT: inbox}))


def test_a_mapping_may_name_the_practice_watched_folder():
    inbox = {"practice": PRACTICE, "folder": "varga", "senders": [SENDER], "inbox": "inbox-a1"}
    inboxes = ses_intake.load_inboxes(json.dumps({"Lakeside-Varga": inbox}))

    assert inboxes["lakeside-varga"].key_for(date(2026, 11, 20), b"%PDF") == (
        f"practices/{PRACTICE}/inbox-a1/varga/2026-11-20/{hashlib.sha256(b'%PDF').hexdigest()}.pdf"
    )
