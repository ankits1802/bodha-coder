from __future__ import annotations

from app.adapters.development_signer import DevelopmentRecordSigner
from app.adapters.kms_signer import KmsRecordSigner, kms_region
from app.adapters.seal_keys import RecordSigner
from app.core.config import Settings

__all__ = ["SigningNotConfigured", "build_record_signer"]


class SigningNotConfigured(RuntimeError):
    pass


def build_record_signer(settings: Settings) -> RecordSigner:
    if settings.signing_key_id:
        return KmsRecordSigner(settings.signing_key_id, kms_region(settings.signing_key_id, settings.s3_region))
    if settings.app_environment == "production":
        raise SigningNotConfigured("SIGNING_KEY_ID must be set when APP_ENVIRONMENT is production")
    return DevelopmentRecordSigner()
