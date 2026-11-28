from __future__ import annotations

import json
from datetime import UTC, datetime
from email.message import EmailMessage

import pytest

from app.core.errors import Invalid
from app.services.email_intake import Gate, refusal_of
from app.services.intake_mail import (
    Envelope,
    ProbeReference,
    local_part_at,
    probe_reference,
    probe_subject,
    read_envelope,
    read_mail,
    sender_allowed,
    sender_pattern,
)
from tests.fakes import text_pdf

NOTE_PDF = text_pdf("Date of service 2026-11-20")
PASSED = {"spam": "PASS", "virus": "PASS", "spf": "PASS", "dkim": "PASS", "dmarc": "PASS"}


def _envelope(**verdicts: str) -> Envelope:
    return Envelope("m1", datetime(2026, 11, 28, tzinfo=UTC), ("a@intake.example.com",), {**PASSED, **verdicts})


def _message(sender: str = "Front Desk <Scans@Lakeside.example.com>") -> EmailMessage:
    message = EmailMessage()
    message["From"] = sender
    message["To"] = "k3j8w2q9x7m4n5p6@intake.example.com"
    message["Subject"] = "Visit notes"
    message.set_content("Notes attached.")
    return message


def test_a_message_gives_its_single_sender_and_only_its_attached_files():
    message = _message()
    message.add_attachment(NOTE_PDF, maintype="application", subtype="pdf", filename="2026-11-20 - 99214.pdf")
    message.add_attachment(b"PK\x03\x04", maintype="application", subtype="msword", filename="scan.doc")
    message.add_attachment(b"\x89PNG logo", maintype="image", subtype="png", disposition="inline")
    mail = read_mail(message.as_bytes())

    assert mail.sender == "scans@lakeside.example.com"
    assert [(item.name, item.is_pdf) for item in mail.attachments] == [
        ("2026-11-20 - 99214.pdf", True),
        ("scan.doc", False),
    ]
    assert mail.attachments[0].data == NOTE_PDF


def test_a_forwarded_message_gives_the_pdf_inside_it():
    inner = _message("Dr Varga <varga@clinic.example.com>")
    inner.add_attachment(NOTE_PDF, maintype="application", subtype="pdf", filename="note.pdf")
    outer = _message()
    outer.add_attachment(inner)
    assert [item.name for item in read_mail(outer.as_bytes()).attachments if item.is_pdf] == ["note.pdf"]


def test_two_from_addresses_give_no_sender():
    assert read_mail(_message("a@lakeside.example.com, b@lakeside.example.com").as_bytes()).sender is None


@pytest.mark.parametrize(
    ("entered", "expected"),
    [
        ("Scans@Lakeside.example.com", ("scans@lakeside.example.com", "address")),
        ("@Lakeside.example.com", ("lakeside.example.com", "domain")),
        ("lakeside.example.com", ("lakeside.example.com", "domain")),
        ("frontdesk.lakeside@gmail.com", ("frontdesk.lakeside@gmail.com", "address")),
    ],
)
def test_a_sender_is_kept_as_one_address_or_one_domain(entered, expected):
    assert sender_pattern(entered) == expected


@pytest.mark.parametrize("entered", ["gmail.com", "@outlook.com", "not an address", "a@b", "a@@lakeside.example.com"])
def test_a_public_mail_service_or_a_malformed_sender_is_refused(entered):
    with pytest.raises(Invalid):
        sender_pattern(entered)


def test_a_sender_is_allowed_by_its_address_or_its_exact_domain():
    allowed = {"scans@lakeside.example.com", "riverbend.example.org"}
    assert sender_allowed("scans@lakeside.example.com", allowed)
    assert sender_allowed("anyone@riverbend.example.org", allowed)
    assert not sender_allowed("billing@lakeside.example.com", allowed)
    assert not sender_allowed("scans@mail.riverbend.example.org", allowed)
    assert not sender_allowed(None, allowed)


def test_only_the_intake_domain_names_a_local_part():
    assert local_part_at("K3J8@Intake.Example.com", "intake.example.com") == "k3j8"
    assert local_part_at("k3j8@example.com", "intake.example.com") is None
    assert local_part_at("intake.example.com", "intake.example.com") is None


def test_a_probe_subject_reads_back_as_its_reference():
    reference = ProbeReference("3f1c2a9e-5b7d-4c11-9e2a-000000000001", "0123456789abcdef0123456789abcdef")
    assert probe_reference(f"Re: {probe_subject(reference)}") == reference
    assert probe_reference("Bodha intake test for the front desk") is None


@pytest.mark.parametrize(
    "stored",
    [
        {"version": 2},
        {"version": 1, "message_id": "a/b", "recipients": ["x@y.example"], "verdicts": {}},
        {"version": 1, "message_id": "m1", "received_at": "2026-11-28T10:00:00", "recipients": ["x@y.example"]},
        {"version": 1, "message_id": "m1", "received_at": "2026-11-28T10:00:00Z", "recipients": [], "verdicts": {}},
    ],
)
def test_an_envelope_of_another_shape_is_refused(stored):
    with pytest.raises(ValueError):
        read_envelope(json.dumps(stored).encode())


def _gate(**changes) -> Gate:
    return Gate(**{"current": True, "practice_open": True, "allowed_senders": {"lakeside.example.com"}, **changes})


def _mail_with_pdf(sender: str = "scans@lakeside.example.com"):
    message = _message(sender)
    message.add_attachment(NOTE_PDF, maintype="application", subtype="pdf", filename="note.pdf")
    return read_mail(message.as_bytes())


def test_a_message_passes_only_every_check_in_order():
    mail = _mail_with_pdf()
    assert refusal_of(_envelope(), mail, _gate()) is None
    assert refusal_of(_envelope(virus="FAIL"), mail, _gate(current=False)) == "retired_address"
    assert refusal_of(_envelope(virus="FAIL"), mail, _gate(practice_open=False)) == "practice_closed"
    assert refusal_of(_envelope(virus="FAIL", dmarc="FAIL"), mail, _gate()) == "failed_scan"
    assert refusal_of(_envelope(dmarc="GRAY"), mail, _gate()) == "not_authenticated"
    assert refusal_of(_envelope(), _mail_with_pdf("someone@elsewhere.example"), _gate()) == "sender_not_allowed"
    assert refusal_of(_envelope(), read_mail(_message("scans@lakeside.example.com").as_bytes()), _gate()) == "no_pdf"
