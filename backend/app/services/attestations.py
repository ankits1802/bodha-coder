from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import ProviderActor
from app.core.errors import Conflict
from app.models import LEVEL_CHANGE_PURPOSE, AddendumRequest, ProviderAttestation
from app.services.note_texts import current_texts, note_texts

__all__ = [
    "ADDENDUM_ATTESTATION",
    "LEVEL_ATTESTATION",
    "Statement",
    "attestation_for",
    "attestation_view",
    "checked_wording",
    "note_attestations",
    "record_attestation",
]

ADDENDUM_ATTESTATION = "This is clinically accurate"
LEVEL_ATTESTATION = "I reviewed the billed and approved visit levels and the evidence shown"
AGENT_LENGTH = 300


@dataclass(frozen=True)
class Statement:
    wording: str
    shown: str
    answer: str
    comment: str | None


def attestation_for(purpose: str) -> str:
    return LEVEL_ATTESTATION if purpose == LEVEL_CHANGE_PURPOSE else ADDENDUM_ATTESTATION


def checked_wording(expected: str, given: str | None) -> str:
    if given is not None and given.strip() != expected:
        raise Conflict("the confirmation wording has changed; reload the page")
    return expected


async def record_attestation(
    db: AsyncSession, actor: ProviderActor, request: AddendumRequest, statement: Statement
) -> ProviderAttestation:
    texts = current_texts(await note_texts(db, request.note_id))
    attestation = ProviderAttestation(
        practice_id=request.practice_id,
        note_id=request.note_id,
        request_id=request.id,
        provider_id=request.provider_id,
        approved_claim_id=request.approved_claim_id,
        purpose=request.purpose,
        wording=statement.wording,
        confirmed=True,
        text_revision_ids=[text.id for text in texts],
        shown=statement.shown,
        answer=statement.answer,
        comment=statement.comment,
        ip=actor.ip,
        user_agent=(actor.user_agent or "")[:AGENT_LENGTH] or None,
    )
    db.add(attestation)
    return attestation


async def note_attestations(db: AsyncSession, note_id: str) -> list[ProviderAttestation]:
    rows = await db.scalars(
        select(ProviderAttestation)
        .where(ProviderAttestation.note_id == note_id)
        .order_by(ProviderAttestation.created_at)
    )
    return list(rows.all())


def attestation_view(row: ProviderAttestation, provider_name: str) -> dict[str, Any]:
    return {
        "id": row.id,
        "at": row.created_at.isoformat(),
        "provider": provider_name,
        "purpose": row.purpose,
        "answer": row.answer,
        "comment": row.comment,
        "wording": row.wording,
        "shown": row.shown,
        "text_revisions": len(row.text_revision_ids),
        "ip": row.ip,
        "user_agent": row.user_agent,
    }
