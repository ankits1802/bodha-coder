from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

import boto3

logger = logging.getLogger("bodha.ses_intake")
logger.setLevel(logging.INFO)

ENVELOPE_VERSION = 1
INBOUND_PREFIX = "ses-inbound/"
ENVELOPE_SUFFIX = ".json"
ENVELOPE_TYPE = "application/json"
BUCKET_VARIABLE = "INTAKE_BUCKET"
MESSAGE_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
VERDICTS = {
    "spam": "spamVerdict",
    "virus": "virusVerdict",
    "spf": "spfVerdict",
    "dkim": "dkimVerdict",
    "dmarc": "dmarcVerdict",
}


def handler(event: dict[str, Any], context: Any) -> dict[str, int]:
    bucket = os.environ[BUCKET_VARIABLE]
    s3 = boto3.client("s3")
    keys = [record_envelope(s3, bucket, envelope_of(record["ses"])) for record in event.get("Records", [])]
    return {"messages": len(keys)}


def envelope_of(ses: dict[str, Any]) -> dict[str, Any]:
    mail, receipt = ses["mail"], ses["receipt"]
    message_id = str(mail.get("messageId", ""))
    if MESSAGE_ID.fullmatch(message_id) is None:
        raise ValueError("SES gave a message id that is not letters, digits, dashes or underscores")
    recipients = sorted({str(item).strip().lower() for item in receipt.get("recipients") or [] if str(item).strip()})
    if not recipients:
        raise ValueError(f"message {message_id} reached the function without a recipient")
    return {
        "version": ENVELOPE_VERSION,
        "message_id": message_id,
        "received_at": str(receipt.get("timestamp") or mail.get("timestamp") or ""),
        "recipients": recipients,
        "verdicts": {name: _status(receipt.get(field)) for name, field in VERDICTS.items()},
    }


def envelope_key(message_id: str) -> str:
    return f"{INBOUND_PREFIX}{message_id}{ENVELOPE_SUFFIX}"


def record_envelope(s3: Any, bucket: str, envelope: dict[str, Any]) -> str:
    key = envelope_key(envelope["message_id"])
    body = json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode("utf-8")
    s3.put_object(Bucket=bucket, Key=key, Body=body, ContentType=ENVELOPE_TYPE)
    entry = {"event": "ses intake", "message": envelope["message_id"], "recipients": len(envelope["recipients"])}
    logger.info(json.dumps(entry))
    return key


def _status(verdict: Any) -> str:
    return str(verdict.get("status", "")).upper() if isinstance(verdict, dict) else ""
