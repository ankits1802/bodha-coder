from __future__ import annotations

import email
import json
import re
from collections.abc import Collection, Mapping
from dataclasses import dataclass
from datetime import datetime
from email import policy
from email.message import EmailMessage
from email.utils import getaddresses
from typing import Any

from app.core.errors import Invalid
from app.services.email_domains import domain_of, is_public_domain, normal_domain

__all__ = [
    "ADDRESS_KIND",
    "DOMAIN_KIND",
    "ENVELOPE_VERSION",
    "INBOUND_PREFIX",
    "MESSAGE_TYPE",
    "RETAINED_PREFIX",
    "Attachment",
    "Envelope",
    "Mail",
    "ProbeReference",
    "envelope_message_id",
    "local_part_at",
    "read_envelope",
    "read_mail",
    "sender_allowed",
    "sender_pattern",
    "probe_reference",
    "probe_subject",
]

ENVELOPE_VERSION = 1
INBOUND_PREFIX = "ses-inbound/"
RETAINED_PREFIX = "ses-retained/"
ENVELOPE_SUFFIX = ".json"
MESSAGE_TYPE = "message/rfc822"
PASS = "PASS"
VERDICT_NAMES = ("spam", "virus", "spf", "dkim", "dmarc")
MESSAGE_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
ADDRESS = re.compile(r"^[a-z0-9.!#$%&'*+/=?^_`{|}~-]{1,64}@[^@\s]{4,253}$")
PROBE_PREFIX = "Bodha intake test"
PROBE_SUBJECT = re.compile(rf"{PROBE_PREFIX} ([0-9a-f-]{{36}})\.([0-9a-f]{{32}})")
PDF_TYPE = "application/pdf"
PDF_SUFFIX = ".pdf"
ADDRESS_KIND = "address"
DOMAIN_KIND = "domain"
NOT_A_SENDER = "enter an email address such as scans@example.com or a domain such as example.com"


@dataclass(frozen=True)
class Envelope:
    message_id: str
    received_at: datetime
    recipients: tuple[str, ...]
    verdicts: Mapping[str, str]

    @property
    def raw_key(self) -> str:
        return f"{INBOUND_PREFIX}{self.message_id}"

    @property
    def envelope_key(self) -> str:
        return f"{self.raw_key}{ENVELOPE_SUFFIX}"

    @property
    def retained_key(self) -> str:
        return f"{RETAINED_PREFIX}{self.message_id}"

    def passed(self, *names: str) -> bool:
        return all(self.verdicts.get(name) == PASS for name in names)


@dataclass(frozen=True)
class Attachment:
    name: str
    content_type: str
    data: bytes

    @property
    def is_pdf(self) -> bool:
        return self.content_type == PDF_TYPE or self.name.lower().endswith(PDF_SUFFIX)


@dataclass(frozen=True)
class Mail:
    senders: tuple[str, ...]
    subject: str
    attachments: tuple[Attachment, ...]

    @property
    def sender(self) -> str | None:
        return self.senders[0] if len(self.senders) == 1 else None


@dataclass(frozen=True)
class ProbeReference:
    test_id: str
    token: str


def envelope_message_id(key: str) -> str | None:
    if not key.startswith(INBOUND_PREFIX) or not key.endswith(ENVELOPE_SUFFIX):
        return None
    found = key[len(INBOUND_PREFIX) : -len(ENVELOPE_SUFFIX)]
    return found if MESSAGE_ID.fullmatch(found) else None


def read_envelope(data: bytes) -> Envelope:
    try:
        stored = json.loads(data)
    except ValueError as error:
        raise ValueError("an intake envelope is not JSON") from error
    if not isinstance(stored, dict) or stored.get("version") != ENVELOPE_VERSION:
        raise ValueError(f"an intake envelope must carry version {ENVELOPE_VERSION}")
    message_id = stored.get("message_id")
    if not isinstance(message_id, str) or MESSAGE_ID.fullmatch(message_id) is None:
        raise ValueError("an intake envelope needs a message id of letters, digits, dashes or underscores")
    return Envelope(message_id, _received_at(stored), _recipients(stored), _verdicts(stored))


def _received_at(stored: dict[str, Any]) -> datetime:
    try:
        received = datetime.fromisoformat(str(stored.get("received_at", "")).replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("an intake envelope needs the time the message was received") from error
    if received.tzinfo is None:
        raise ValueError("an intake envelope's received time needs a time zone")
    return received


def _recipients(stored: dict[str, Any]) -> tuple[str, ...]:
    listed = stored.get("recipients")
    if not isinstance(listed, list) or not listed or not all(isinstance(item, str) for item in listed):
        raise ValueError("an intake envelope needs its recipients")
    return tuple(sorted({item.strip().lower() for item in listed}))


def _verdicts(stored: dict[str, Any]) -> dict[str, str]:
    found = stored.get("verdicts")
    if not isinstance(found, dict):
        raise ValueError("an intake envelope needs the SES verdicts")
    return {name: str(found.get(name, "")).upper() for name in VERDICT_NAMES}


def read_mail(raw: bytes) -> Mail:
    message = email.message_from_bytes(raw, policy=policy.default)
    if not isinstance(message, EmailMessage):
        raise ValueError("a stored intake message could not be read")
    listed = getaddresses([str(value) for value in message.get_all("From", [])])
    senders = tuple(address.strip().lower() for _, address in listed if address.strip())
    return Mail(senders, str(message.get("Subject", "")), tuple(_attachments(message)))


def _attachments(message: EmailMessage) -> list[Attachment]:
    found: list[Attachment] = []
    for part in message.walk():
        if part.is_multipart():
            continue
        name = part.get_filename() or ""
        attached = part.get_content_disposition() == "attachment"
        if not attached and part.get_content_type() != PDF_TYPE and not name.lower().endswith(PDF_SUFFIX):
            continue
        data = part.get_payload(decode=True)
        if isinstance(data, bytes):
            found.append(Attachment(name, part.get_content_type(), data))
    return found


def sender_pattern(text: str) -> tuple[str, str]:
    entered = text.strip().lower()
    if "@" not in entered.removeprefix("@"):
        domain = normal_domain(entered)
        if is_public_domain(domain):
            raise Invalid(f"allow addresses at {domain} one at a time; a public email service cannot be allowed whole")
        return domain, DOMAIN_KIND
    domain = domain_of(entered)
    if ADDRESS.fullmatch(entered) is None or domain is None:
        raise Invalid(NOT_A_SENDER)
    normal_domain(domain)
    return entered, ADDRESS_KIND


def sender_allowed(sender: str | None, patterns: Collection[str]) -> bool:
    if not sender:
        return False
    return sender in patterns or domain_of(sender) in patterns


def local_part_at(recipient: str, domain: str) -> str | None:
    local, at, host = recipient.strip().lower().rpartition("@")
    return local if at and local and host == domain.lower() else None


def probe_subject(reference: ProbeReference) -> str:
    return f"{PROBE_PREFIX} {reference.test_id}.{reference.token}"


def probe_reference(subject: str) -> ProbeReference | None:
    found = PROBE_SUBJECT.search(subject)
    return ProbeReference(found.group(1), found.group(2)) if found else None
