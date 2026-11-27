from __future__ import annotations

import hashlib

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import Prehashed

from app.adapters.seal_keys import Seal, check_digest, ecdsa_valid

__all__ = ["DEVELOPMENT_KEY_ID", "DevelopmentRecordSigner"]

DEVELOPMENT_KEY_ID = "development"
DEVELOPMENT_SEED = b"bodha-assure development record seal, never for real records"
P256_ORDER = 0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551


class DevelopmentRecordSigner:
    def __init__(self) -> None:
        scalar = int.from_bytes(hashlib.sha256(DEVELOPMENT_SEED).digest(), "big") % (P256_ORDER - 1) + 1
        self._private_key = ec.derive_private_key(scalar, ec.SECP256R1())

    @property
    def key_id(self) -> str:
        return DEVELOPMENT_KEY_ID

    async def sign_digest(self, digest: bytes) -> Seal:
        signature = self._private_key.sign(check_digest(digest), ec.ECDSA(Prehashed(hashes.SHA256())))
        return Seal(signature, DEVELOPMENT_KEY_ID)

    async def verify_digest(self, digest: bytes, signature: bytes, *, key_id: str) -> bool:
        if key_id != DEVELOPMENT_KEY_ID:
            return False
        return ecdsa_valid(self._private_key.public_key(), digest, signature)
