from typing import Literal

from app.models import SIGNATURE_SOURCES, SIGNER_KINDS, SIGNING_EVENTS
from app.services.seal_verification import PROBLEMS

from .view import View

__all__ = ["MySignature", "SealVerification", "SignatureSource", "SignatureView", "SigningEventType"]

SignatureSource = Literal[SIGNATURE_SOURCES]
SigningEventType = Literal[SIGNING_EVENTS]
SignerKind = Literal[SIGNER_KINDS]
VerificationProblem = Literal[PROBLEMS]


class SignatureView(View):
    id: str
    source: SignatureSource
    typed_name: str
    image: str
    created_at: str


class MySignature(View):
    signature: SignatureView | None


class SealVerification(View):
    valid: bool
    problems: list[VerificationProblem]
    code: str
    event: SigningEventType
    practice_name: str
    signer_kind: SignerKind
    signer_name: str
    signer_title: str
    signed_at: str
    document_sha256: str | None
    envelope_sha256: str
