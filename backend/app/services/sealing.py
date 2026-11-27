from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.seal_keys import RecordSigner, Seal
from app.core.deps import Actor, Client, ProviderActor
from app.models import (
    LEVEL_CHANGE_PURPOSE,
    SEAL_SCHEMA_VERSION,
    ApprovedClaim,
    Note,
    Practice,
    Provider,
    ProviderAttestation,
    Signature,
    SigningEvent,
    User,
    utcnow,
)
from app.services.sealed_records import (
    AGREEMENT_EVENT,
    agreement_record,
    attestation_record,
    record_digest,
    snapshot_record,
)
from app.services.signature_envelope import EnvelopeFacts, SignerIdentity, envelope_text, new_verification_code

__all__ = [
    "PERSON",
    "PROVIDER",
    "SealedRecord",
    "SignedBy",
    "agreement_signer",
    "facts_of",
    "person_signer",
    "provider_event",
    "provider_signer",
    "seal_agreement",
    "seal_attestation",
    "seal_snapshot",
]

AGENT_LENGTH = 300
IP_LENGTH = 64
PERSON, PROVIDER = "user", "provider"


@dataclass(frozen=True)
class SignedBy:
    identity: SignerIdentity
    signature: Signature | None
    ip: str | None
    user_agent: str | None


@dataclass(frozen=True)
class SealedRecord:
    event: str
    practice_id: str
    note_id: str | None
    record_id: str
    statement: str
    content_sha256: str
    document_sha256: str | None


def person_signer(actor: Actor, signature: Signature) -> SignedBy:
    user = actor.user
    identity = SignerIdentity(PERSON, user.id, user.name, actor.role, signature.typed_name)
    return SignedBy(identity, signature, actor.ip, actor.user_agent)


def provider_signer(actor: ProviderActor, provider: Provider, signature: Signature) -> SignedBy:
    identity = SignerIdentity(PROVIDER, provider.id, provider.name, provider.credential, signature.typed_name)
    return SignedBy(identity, signature, actor.ip, actor.user_agent)


def agreement_signer(user: User, role: str, client: Client) -> SignedBy:
    return SignedBy(SignerIdentity(PERSON, user.id, user.name, role, user.name), None, client.ip, client.agent)


def provider_event(purpose: str) -> str:
    return "provider_level_change" if purpose == LEVEL_CHANGE_PURPOSE else "provider_addendum"


async def seal_snapshot(
    db: AsyncSession, signer: RecordSigner, signed_by: SignedBy, snapshot: ApprovedClaim, *, event: str, statement: str
) -> SigningEvent:
    record = SealedRecord(
        event,
        snapshot.practice_id,
        snapshot.note_id,
        snapshot.id,
        statement,
        record_digest(snapshot_record(snapshot)),
        snapshot.document_sha256,
    )
    return await _sealed(db, signer, signed_by, record)


async def seal_attestation(
    db: AsyncSession, signer: RecordSigner, signed_by: SignedBy, attestation: ProviderAttestation, note: Note
) -> SigningEvent:
    await db.flush()
    record = SealedRecord(
        provider_event(attestation.purpose),
        note.practice_id,
        note.id,
        attestation.id,
        attestation.wording,
        record_digest(attestation_record(attestation)),
        note.file_sha256,
    )
    return await _sealed(db, signer, signed_by, record)


async def seal_agreement(
    db: AsyncSession, signer: RecordSigner, signed_by: SignedBy, practice: Practice, *, statement: str
) -> SigningEvent:
    await db.flush()
    accepted = agreement_record(practice)
    if accepted is None:
        raise ValueError(f"practice {practice.id} has no accepted agreement to seal")
    record = SealedRecord(AGREEMENT_EVENT, practice.id, None, practice.id, statement, record_digest(accepted), None)
    return await _sealed(db, signer, signed_by, record)


def facts_of(row: SigningEvent) -> EnvelopeFacts:
    signer_id = row.signer_user_id if row.signer_kind == PERSON else row.signer_provider_id
    identity = SignerIdentity(row.signer_kind, signer_id or "", row.signer_name, row.signer_title, row.typed_name)
    return EnvelopeFacts(
        event=row.event,
        practice_id=row.practice_id,
        note_id=row.note_id,
        record_id=row.record_id,
        statement=row.statement,
        signer=identity,
        signature_sha256=row.signature_sha256,
        document_sha256=row.document_sha256,
        content_sha256=row.content_sha256,
        signed_at=row.signed_at,
        ip=row.ip,
        user_agent=row.user_agent,
    )


async def _sealed(db: AsyncSession, signer: RecordSigner, signed_by: SignedBy, record: SealedRecord) -> SigningEvent:
    signature = signed_by.signature
    facts = EnvelopeFacts(
        event=record.event,
        practice_id=record.practice_id,
        note_id=record.note_id,
        record_id=record.record_id,
        statement=record.statement,
        signer=signed_by.identity,
        signature_sha256=signature.sha256 if signature is not None else None,
        document_sha256=record.document_sha256,
        content_sha256=record.content_sha256,
        signed_at=utcnow(),
        ip=(signed_by.ip or "")[:IP_LENGTH] or None,
        user_agent=(signed_by.user_agent or "")[:AGENT_LENGTH] or None,
    )
    envelope = envelope_text(facts)
    seal = await signer.sign_digest(hashlib.sha256(envelope).digest())
    row = _event_row(facts, signature.id if signature is not None else None, envelope, seal)
    db.add(row)
    await db.flush()
    return row


def _event_row(facts: EnvelopeFacts, signature_id: str | None, envelope: bytes, seal: Seal) -> SigningEvent:
    identity = facts.signer
    return SigningEvent(
        practice_id=facts.practice_id,
        note_id=facts.note_id,
        event=facts.event,
        record_id=facts.record_id,
        statement=facts.statement,
        signer_kind=identity.kind,
        signer_user_id=identity.id if identity.kind == PERSON else None,
        signer_provider_id=identity.id if identity.kind == PROVIDER else None,
        signer_name=identity.name,
        signer_title=identity.title,
        typed_name=identity.typed_name,
        signature_id=signature_id,
        signature_sha256=facts.signature_sha256,
        document_sha256=facts.document_sha256,
        content_sha256=facts.content_sha256,
        signed_at=facts.signed_at,
        ip=facts.ip,
        user_agent=facts.user_agent,
        code=new_verification_code(),
        schema_version=SEAL_SCHEMA_VERSION,
        envelope=envelope.decode(),
        envelope_sha256=hashlib.sha256(envelope).hexdigest(),
        seal=base64.b64encode(seal.signature).decode("ascii"),
        seal_key_id=seal.key_id,
        seal_algorithm=seal.algorithm,
    )
