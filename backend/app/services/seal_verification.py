from __future__ import annotations

import base64
import binascii
import hashlib
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.object_store import ObjectStore
from app.adapters.seal_keys import RecordSigner
from app.core.errors import NotFound
from app.models import Practice, Signature, SigningEvent
from app.services.rate_limits import VERIFY_PER_IP, hit
from app.services.sealed_records import record_digest, source_record
from app.services.sealing import facts_of
from app.services.signature_envelope import envelope_text, normal_code, sha256_hex

__all__ = ["PROBLEMS", "SealCheck", "check_event", "verify_code"]

RECORD_MISSING = "record_missing"
RECORD_CHANGED = "record_changed"
SIGNATURE_MISSING = "signature_missing"
SIGNATURE_CHANGED = "signature_changed"
ENVELOPE_CHANGED = "envelope_changed"
SEAL_INVALID = "seal_invalid"
PROBLEMS = (RECORD_MISSING, RECORD_CHANGED, SIGNATURE_MISSING, SIGNATURE_CHANGED, ENVELOPE_CHANGED, SEAL_INVALID)
UNKNOWN_CODE = "no signed record has that verification code"


@dataclass(frozen=True)
class SealCheck:
    event: SigningEvent
    practice_name: str
    problems: tuple[str, ...]

    @property
    def valid(self) -> bool:
        return not self.problems


async def verify_code(
    db: AsyncSession, store: ObjectStore, signer: RecordSigner, code: str, *, ip: str | None
) -> SealCheck:
    await hit(db, VERIFY_PER_IP, ip)
    normal = normal_code(code)
    row = await db.scalar(select(SigningEvent).where(SigningEvent.code == normal)) if normal else None
    if row is None:
        raise NotFound(UNKNOWN_CODE)
    return await check_event(db, store, signer, row)


async def check_event(db: AsyncSession, store: ObjectStore, signer: RecordSigner, row: SigningEvent) -> SealCheck:
    problems = [
        *await _record_problems(db, row),
        *await _image_problems(db, store, row),
        *await _seal_problems(signer, row),
    ]
    practice = await db.get(Practice, row.practice_id)
    return SealCheck(row, practice.name if practice else "", tuple(problems))


async def _record_problems(db: AsyncSession, row: SigningEvent) -> list[str]:
    record = await source_record(db, row.event, row.record_id)
    if record is None:
        return [RECORD_MISSING]
    return [] if record_digest(record) == row.content_sha256 else [RECORD_CHANGED]


async def _image_problems(db: AsyncSession, store: ObjectStore, row: SigningEvent) -> list[str]:
    if row.signature_id is None:
        return [] if row.signature_sha256 is None else [SIGNATURE_MISSING]
    signature = await db.get(Signature, row.signature_id)
    if signature is None or not await store.exists(signature.file_key):
        return [SIGNATURE_MISSING]
    stored = sha256_hex(await store.get(signature.file_key))
    return [] if stored == signature.sha256 == row.signature_sha256 else [SIGNATURE_CHANGED]


async def _seal_problems(signer: RecordSigner, row: SigningEvent) -> list[str]:
    rebuilt = envelope_text(facts_of(row))
    same = rebuilt.decode() == row.envelope and sha256_hex(rebuilt) == row.envelope_sha256
    problems = [] if same else [ENVELOPE_CHANGED]
    return problems if await _sealed(signer, rebuilt, row) else [*problems, SEAL_INVALID]


async def _sealed(signer: RecordSigner, envelope: bytes, row: SigningEvent) -> bool:
    try:
        signature = base64.b64decode(row.seal, validate=True)
    except (binascii.Error, ValueError):
        return False
    return await signer.verify_digest(hashlib.sha256(envelope).digest(), signature, key_id=row.seal_key_id)
