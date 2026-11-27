from __future__ import annotations

import hashlib
import json
import re
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from app.models import SEAL_SCHEMA_VERSION

__all__ = [
    "CODE_ALPHABET",
    "CODE_GROUPS",
    "EnvelopeFacts",
    "SignerIdentity",
    "canonical_json",
    "envelope_of",
    "envelope_text",
    "new_verification_code",
    "normal_code",
    "sha256_hex",
    "utc_text",
]

CODE_ALPHABET = "ABCDEFGHJKMNPQRSTVWXYZ23456789"
CODE_GROUPS = 3
CODE_GROUP_LENGTH = 4
_CODE_SEPARATORS = re.compile(r"[\s-]+")


@dataclass(frozen=True)
class SignerIdentity:
    kind: str
    id: str
    name: str
    title: str
    typed_name: str


@dataclass(frozen=True)
class EnvelopeFacts:
    event: str
    practice_id: str
    note_id: str | None
    record_id: str
    statement: str
    signer: SignerIdentity
    signature_sha256: str | None
    document_sha256: str | None
    content_sha256: str
    signed_at: datetime
    ip: str | None
    user_agent: str | None


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def utc_text(moment: datetime) -> str:
    if moment.tzinfo is None:
        raise ValueError("a signing time must carry a time zone")
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def envelope_of(facts: EnvelopeFacts) -> dict[str, Any]:
    signer = facts.signer
    return {
        "version": SEAL_SCHEMA_VERSION,
        "event": facts.event,
        "practice_id": facts.practice_id,
        "note_id": facts.note_id,
        "record_id": facts.record_id,
        "statement": facts.statement,
        "signer": {
            "kind": signer.kind,
            "id": signer.id,
            "name": signer.name,
            "title": signer.title,
            "typed_name": signer.typed_name,
        },
        "signature_sha256": facts.signature_sha256,
        "document_sha256": facts.document_sha256,
        "content_sha256": facts.content_sha256,
        "signed_at": utc_text(facts.signed_at),
        "ip": facts.ip,
        "user_agent": facts.user_agent,
    }


def envelope_text(facts: EnvelopeFacts) -> bytes:
    return canonical_json(envelope_of(facts))


def new_verification_code() -> str:
    groups = ("".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_GROUP_LENGTH)) for _ in range(CODE_GROUPS))
    return "-".join(groups)


def normal_code(text: str) -> str | None:
    bare = _CODE_SEPARATORS.sub("", text).upper()
    if len(bare) != CODE_GROUPS * CODE_GROUP_LENGTH or any(letter not in CODE_ALPHABET for letter in bare):
        return None
    return "-".join(bare[start : start + CODE_GROUP_LENGTH] for start in range(0, len(bare), CODE_GROUP_LENGTH))
