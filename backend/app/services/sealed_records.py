from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ApprovedClaim, Practice, ProviderAttestation
from app.services.signature_envelope import canonical_json, sha256_hex, utc_text

__all__ = [
    "AGREEMENT_EVENT",
    "APPROVAL_EVENT",
    "APPROVAL_EVENTS",
    "COMPLIANCE_EVENT",
    "PROVIDER_EVENTS",
    "agreement_record",
    "attestation_record",
    "record_digest",
    "snapshot_record",
    "source_record",
]

APPROVAL_EVENT = "approval"
COMPLIANCE_EVENT = "compliance_decision"
APPROVAL_EVENTS = (APPROVAL_EVENT, COMPLIANCE_EVENT)
PROVIDER_EVENTS = ("provider_addendum", "provider_level_change")
AGREEMENT_EVENT = "agreement"


def snapshot_record(row: ApprovedClaim) -> dict[str, Any]:
    return {
        "id": row.id,
        "practice_id": row.practice_id,
        "note_id": row.note_id,
        "revision": row.revision,
        "final_code_set_id": row.final_code_set_id,
        "approved_by": row.approved_by,
        "approver_name": row.approver_name,
        "approver_role": row.approver_role,
        "approved_at": utc_text(row.approved_at),
        "analysis_id": row.analysis_id,
        "model": row.model,
        "prompt_version": row.prompt_version,
        "text_revision_ids": list(row.text_revision_ids),
        "document_key": row.document_key,
        "document_sha256": row.document_sha256,
        "schema_version": row.schema_version,
        "content": row.content,
    }


def attestation_record(row: ProviderAttestation) -> dict[str, Any]:
    return {
        "id": row.id,
        "practice_id": row.practice_id,
        "note_id": row.note_id,
        "request_id": row.request_id,
        "provider_id": row.provider_id,
        "approved_claim_id": row.approved_claim_id,
        "purpose": row.purpose,
        "wording": row.wording,
        "confirmed": row.confirmed,
        "text_revision_ids": list(row.text_revision_ids),
        "shown": row.shown,
        "answer": row.answer,
        "comment": row.comment,
    }


def agreement_record(practice: Practice) -> dict[str, Any] | None:
    return {"practice_id": practice.id, "signup": practice.signup} if practice.signup else None


def record_digest(record: dict[str, Any]) -> str:
    return sha256_hex(canonical_json(record))


async def source_record(db: AsyncSession, event: str, record_id: str) -> dict[str, Any] | None:
    if event in APPROVAL_EVENTS:
        snapshot = await db.get(ApprovedClaim, record_id)
        return None if snapshot is None else snapshot_record(snapshot)
    if event in PROVIDER_EVENTS:
        attestation = await db.get(ProviderAttestation, record_id)
        return None if attestation is None else attestation_record(attestation)
    if event == AGREEMENT_EVENT:
        practice = await db.get(Practice, record_id)
        return None if practice is None else agreement_record(practice)
    raise ValueError(f"not a signing event: {event!r}")
