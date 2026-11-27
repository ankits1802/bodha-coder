from __future__ import annotations

import email
import hashlib
import json
import logging
import os
import re
from dataclasses import dataclass
from datetime import date
from email import policy
from email.message import Message
from email.utils import getaddresses
from typing import Any
from urllib.parse import unquote_plus

import boto3

logger = logging.getLogger("bodha.ses_intake")
logger.setLevel(logging.INFO)

RAW_PREFIX = "ses-inbound/"
RETAINED_PREFIX = "ses-retained/"
MESSAGE_TYPE = "message/rfc822"
ADDRESSES_VARIABLE = "INTAKE_ADDRESSES"
DEFAULT_INBOX = "inbox"
PDF_TYPE = "application/pdf"
PDF_SUFFIX = ".pdf"
PDF_MAGIC = b"%PDF"
PASS = "PASS"
VERDICT_HEADERS = ("X-SES-Spam-Verdict", "X-SES-Virus-Verdict")
SERVICE_DAY = re.compile(r"(?<!\d)(\d{4}-\d{2}-\d{2})(?!\d)")
PRACTICE_ID = re.compile(r"^[A-Za-z0-9-]{1,36}$")
FOLDER_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,59}$")
INBOX_NAME = re.compile(r"^inbox(-[a-z0-9]{1,30})?$")
RESERVED_FOLDERS = frozenset({"processed", "rejected"})


@dataclass(frozen=True)
class Inbox:
    practice: str
    folder: str
    senders: frozenset[str]
    prefix: str = DEFAULT_INBOX

    def key_for(self, day: date, data: bytes) -> str:
        checksum = hashlib.sha256(data).hexdigest()
        return f"practices/{self.practice}/{self.prefix}/{self.folder}/{day.isoformat()}/{checksum}{PDF_SUFFIX}"


@dataclass(frozen=True)
class Outcome:
    result: str
    practice: str | None = None
    written: int = 0

    def as_log(self) -> dict[str, Any]:
        return {"event": "ses intake", "result": self.result, "practice": self.practice, "written": self.written}


def handler(event: dict[str, Any], context: Any) -> dict[str, int]:
    inboxes = load_inboxes(os.environ[ADDRESSES_VARIABLE])
    outcomes = process_event(boto3.client("s3"), inboxes, event)
    return {"messages": len(outcomes), "written": sum(outcome.written for outcome in outcomes)}


def load_inboxes(text: str) -> dict[str, Inbox]:
    mapping = json.loads(text)
    if not isinstance(mapping, dict) or not mapping:
        raise ValueError(f"{ADDRESSES_VARIABLE} must map each recipient to an inbox")
    return {str(recipient).strip().lower(): _inbox(value) for recipient, value in mapping.items()}


def _inbox(value: Any) -> Inbox:
    if not isinstance(value, dict):
        raise ValueError("each inbox must be an object")
    inbox = Inbox(
        practice=str(value.get("practice", "")),
        folder=str(value.get("folder", "")),
        senders=frozenset(str(sender).strip().lower() for sender in value.get("senders") or []),
        prefix=str(value.get("inbox") or DEFAULT_INBOX),
    )
    if PRACTICE_ID.fullmatch(inbox.practice) is None:
        raise ValueError("each inbox needs a practice id")
    if FOLDER_NAME.fullmatch(inbox.folder) is None or inbox.folder.lower() in RESERVED_FOLDERS:
        raise ValueError(f"the inbox of practice {inbox.practice} needs a provider folder that is not reserved")
    if INBOX_NAME.fullmatch(inbox.prefix) is None:
        raise ValueError(f"the inbox of practice {inbox.practice} must be inbox or inbox-<letters and digits>")
    if not inbox.senders:
        raise ValueError(f"the inbox of practice {inbox.practice} needs at least one allowed sender")
    return inbox


def process_event(s3: Any, inboxes: dict[str, Inbox], event: dict[str, Any]) -> list[Outcome]:
    outcomes = []
    for record in event.get("Records", []):
        bucket = record["s3"]["bucket"]["name"]
        key = unquote_plus(record["s3"]["object"]["key"])
        recipient = recipient_of(key)
        raw = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
        s3.put_object(Bucket=bucket, Key=retained_key(key), Body=raw, ContentType=MESSAGE_TYPE)
        outcome = deliver(s3, bucket, inboxes.get(recipient), raw)
        s3.delete_object(Bucket=bucket, Key=key)
        logger.info(json.dumps(outcome.as_log()))
        outcomes.append(outcome)
    return outcomes


def recipient_of(key: str) -> str:
    parts = key[len(RAW_PREFIX) :].split("/") if key.startswith(RAW_PREFIX) else []
    if len(parts) != 2 or not all(parts):
        raise ValueError(f"not a stored message under {RAW_PREFIX}<recipient>/")
    return parts[0].lower()


def retained_key(key: str) -> str:
    recipient_of(key)
    return RETAINED_PREFIX + key[len(RAW_PREFIX) :]


def deliver(s3: Any, bucket: str, inbox: Inbox | None, raw: bytes) -> Outcome:
    if inbox is None:
        return Outcome("unknown_recipient")
    message = email.message_from_bytes(raw, policy=policy.default)
    refusal = refusal_of(message, inbox)
    if refusal is not None:
        return Outcome(refusal, inbox.practice)
    day = service_day(str(message.get("Subject", "")))
    if day is None:
        return Outcome("no_date", inbox.practice)
    keys = {inbox.key_for(day, data): data for data in pdf_attachments(message)}
    for key, data in keys.items():
        s3.put_object(Bucket=bucket, Key=key, Body=data, ContentType=PDF_TYPE)
    return Outcome("delivered" if keys else "no_pdf", inbox.practice, len(keys))


def refusal_of(message: Message, inbox: Inbox) -> str | None:
    for header in VERDICT_HEADERS:
        verdicts = [str(value).strip().upper() for value in message.get_all(header, [])]
        if not verdicts or any(verdict != PASS for verdict in verdicts):
            return "verdict_failed"
    senders = [address.lower() for _, address in getaddresses([str(value) for value in message.get_all("From", [])])]
    if len(senders) != 1 or senders[0] not in inbox.senders:
        return "sender_refused"
    return None


def service_day(subject: str) -> date | None:
    found = SERVICE_DAY.search(subject)
    if found is None:
        return None
    try:
        return date.fromisoformat(found.group(1))
    except ValueError:
        return None


def pdf_attachments(message: Message) -> list[bytes]:
    found = []
    for part in message.walk():
        if part.is_multipart():
            continue
        named_pdf = (part.get_filename() or "").lower().endswith(PDF_SUFFIX)
        if part.get_content_type() != PDF_TYPE and not named_pdf:
            continue
        data = part.get_payload(decode=True)
        if isinstance(data, bytes) and data.startswith(PDF_MAGIC):
            found.append(data)
    return found
