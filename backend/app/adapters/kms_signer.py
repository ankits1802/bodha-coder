from __future__ import annotations

import asyncio
import logging
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import load_der_public_key

from app.adapters.seal_keys import SEAL_ALGORITHM, Seal, check_digest, ecdsa_valid
from app.core.errors import Unavailable

__all__ = ["SEAL_REFUSED", "UNKNOWN_KEY_ERRORS", "KmsRecordSigner", "kms_region"]

logger = logging.getLogger("bodha.seals")
SEAL_REFUSED = "the record could not be sealed, so nothing was saved; try again"
CHECK_REFUSED = "the seal cannot be checked right now; try again"
UNKNOWN_KEY_ERRORS = frozenset(
    {"NotFoundException", "AccessDeniedException", "InvalidArnException", "DisabledException"}
)
ARN_PARTS = 6


def kms_region(key_id: str, fallback: str) -> str:
    parts = key_id.split(":")
    return parts[3] if len(parts) >= ARN_PARTS and parts[0] == "arn" and parts[3] else fallback


class KmsRecordSigner:
    def __init__(self, key_id: str, region: str, *, client: Any = None) -> None:
        self._key_id = key_id
        self._client: Any = client or boto3.client(
            "kms", region_name=region, config=Config(retries={"max_attempts": 5, "mode": "standard"})
        )
        self._public_keys: dict[str, ec.EllipticCurvePublicKey] = {}

    @property
    def key_id(self) -> str:
        return self._key_id

    async def sign_digest(self, digest: bytes) -> Seal:
        try:
            answer = await asyncio.to_thread(
                self._client.sign,
                KeyId=self._key_id,
                Message=check_digest(digest),
                MessageType="DIGEST",
                SigningAlgorithm=SEAL_ALGORITHM,
            )
        except (BotoCoreError, ClientError) as error:
            logger.warning("KMS did not seal a record (%s)", type(error).__name__)
            raise Unavailable(SEAL_REFUSED) from error
        return Seal(answer["Signature"], answer.get("KeyId") or self._key_id)

    async def verify_digest(self, digest: bytes, signature: bytes, *, key_id: str) -> bool:
        public_key = await self._public_key(key_id)
        return public_key is not None and ecdsa_valid(public_key, digest, signature)

    async def _public_key(self, key_id: str) -> ec.EllipticCurvePublicKey | None:
        cached = self._public_keys.get(key_id)
        if cached is not None:
            return cached
        try:
            answer = await asyncio.to_thread(self._client.get_public_key, KeyId=key_id)
        except ClientError as error:
            if error.response.get("Error", {}).get("Code") in UNKNOWN_KEY_ERRORS:
                return None
            raise Unavailable(CHECK_REFUSED) from error
        except BotoCoreError as error:
            raise Unavailable(CHECK_REFUSED) from error
        key = load_der_public_key(answer["PublicKey"])
        if not isinstance(key, ec.EllipticCurvePublicKey):
            return None
        self._public_keys[key_id] = key
        return key
