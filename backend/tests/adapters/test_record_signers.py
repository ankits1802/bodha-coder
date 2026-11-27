import hashlib
from dataclasses import dataclass, field
from typing import Any

import pytest
from botocore.exceptions import ClientError
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import Prehashed

from app.adapters.development_signer import DEVELOPMENT_KEY_ID, DevelopmentRecordSigner
from app.adapters.kms_signer import KmsRecordSigner, kms_region
from app.adapters.record_signers import SigningNotConfigured, build_record_signer
from app.core.config import Settings
from app.core.errors import Unavailable

KEY_ARN = "arn:aws:kms:us-east-2:123456789012:key/1234abcd-12ab-34cd-56ef-1234567890ab"
DIGEST = hashlib.sha256(b"an envelope").digest()


def settings(**values) -> Settings:
    base = {"secret_key": "test-only-secret-key-that-is-long-enough-000", "s3_bucket": "test-bucket"}
    return Settings(_env_file=None, **{**base, **values})


@dataclass
class FakeKms:
    key: ec.EllipticCurvePrivateKey = field(default_factory=lambda: ec.generate_private_key(ec.SECP256R1()))
    signed: list[dict[str, Any]] = field(default_factory=list)
    lookups: list[str] = field(default_factory=list)
    unavailable: bool = False

    def sign(self, **request: Any) -> dict[str, Any]:
        if self.unavailable:
            raise ClientError({"Error": {"Code": "KMSInternalException"}}, "Sign")
        self.signed.append(request)
        signature = self.key.sign(request["Message"], ec.ECDSA(Prehashed(hashes.SHA256())))
        return {"Signature": signature, "KeyId": request["KeyId"], "SigningAlgorithm": request["SigningAlgorithm"]}

    def get_public_key(self, *, KeyId: str) -> dict[str, Any]:
        self.lookups.append(KeyId)
        if KeyId != KEY_ARN:
            raise ClientError({"Error": {"Code": "NotFoundException"}}, "GetPublicKey")
        der = self.key.public_key().public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return {"PublicKey": der, "KeySpec": "ECC_NIST_P256"}


async def test_the_development_signer_seals_and_checks_with_its_fixed_key():
    first, second = DevelopmentRecordSigner(), DevelopmentRecordSigner()
    seal = await first.sign_digest(DIGEST)

    assert (seal.key_id, seal.algorithm) == (DEVELOPMENT_KEY_ID, "ECDSA_SHA_256")
    assert await second.verify_digest(DIGEST, seal.signature, key_id=DEVELOPMENT_KEY_ID)
    assert not await second.verify_digest(
        hashlib.sha256(b"changed").digest(), seal.signature, key_id=DEVELOPMENT_KEY_ID
    )
    assert not await second.verify_digest(DIGEST, seal.signature, key_id=KEY_ARN)


async def test_a_digest_must_be_thirty_two_bytes():
    with pytest.raises(ValueError, match="32 bytes"):
        await DevelopmentRecordSigner().sign_digest(b"not a digest")


async def test_kms_signs_the_digest_itself_with_ecdsa_sha_256():
    kms = FakeKms()
    signer = KmsRecordSigner(KEY_ARN, "us-east-2", client=kms)

    seal = await signer.sign_digest(DIGEST)

    assert kms.signed == [
        {"KeyId": KEY_ARN, "Message": DIGEST, "MessageType": "DIGEST", "SigningAlgorithm": "ECDSA_SHA_256"}
    ]
    assert seal.key_id == KEY_ARN
    assert await signer.verify_digest(DIGEST, seal.signature, key_id=KEY_ARN)
    assert await signer.verify_digest(DIGEST, seal.signature, key_id=KEY_ARN)
    assert kms.lookups == [KEY_ARN]


async def test_kms_answers_invalid_for_another_key_and_for_a_development_seal():
    kms = FakeKms()
    signer = KmsRecordSigner(KEY_ARN, "us-east-2", client=kms)
    development = await DevelopmentRecordSigner().sign_digest(DIGEST)

    assert not await signer.verify_digest(DIGEST, development.signature, key_id=DEVELOPMENT_KEY_ID)
    assert not await signer.verify_digest(DIGEST, development.signature, key_id=KEY_ARN)


async def test_a_kms_failure_saves_nothing_and_says_so():
    signer = KmsRecordSigner(KEY_ARN, "us-east-2", client=FakeKms(unavailable=True))
    with pytest.raises(Unavailable, match="could not be sealed"):
        await signer.sign_digest(DIGEST)


def test_production_refuses_to_start_without_a_signing_key():
    with pytest.raises(SigningNotConfigured, match="SIGNING_KEY_ID"):
        build_record_signer(settings(app_environment="production", signing_key_id=None))
    with pytest.raises(SigningNotConfigured):
        build_record_signer(settings(app_environment="production", signing_key_id="  "))


def test_the_development_key_is_used_only_without_a_key_outside_production():
    assert isinstance(build_record_signer(settings(app_environment="development")), DevelopmentRecordSigner)
    assert isinstance(build_record_signer(settings(app_environment="staging")), DevelopmentRecordSigner)
    built = build_record_signer(settings(app_environment="production", signing_key_id=KEY_ARN))
    assert isinstance(built, KmsRecordSigner) and built.key_id == KEY_ARN


def test_the_kms_region_comes_from_the_key_arn():
    assert kms_region(KEY_ARN, "us-east-1") == "us-east-2"
    assert kms_region("alias/bodha-signing", "us-east-1") == "us-east-1"
