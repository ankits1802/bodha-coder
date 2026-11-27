from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import Prehashed

__all__ = ["DIGEST_BYTES", "SEAL_ALGORITHM", "RecordSigner", "Seal", "check_digest", "ecdsa_valid"]

SEAL_ALGORITHM = "ECDSA_SHA_256"
DIGEST_BYTES = 32


@dataclass(frozen=True)
class Seal:
    signature: bytes
    key_id: str
    algorithm: str = SEAL_ALGORITHM


class RecordSigner(Protocol):
    @property
    def key_id(self) -> str: ...

    async def sign_digest(self, digest: bytes) -> Seal: ...

    async def verify_digest(self, digest: bytes, signature: bytes, *, key_id: str) -> bool: ...


def check_digest(digest: bytes) -> bytes:
    if len(digest) != DIGEST_BYTES:
        raise ValueError(f"a SHA-256 digest is {DIGEST_BYTES} bytes, not {len(digest)}")
    return digest


def ecdsa_valid(public_key: ec.EllipticCurvePublicKey, digest: bytes, signature: bytes) -> bool:
    try:
        public_key.verify(signature, check_digest(digest), ec.ECDSA(Prehashed(hashes.SHA256())))
    except InvalidSignature:
        return False
    return True
