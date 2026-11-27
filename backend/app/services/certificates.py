from __future__ import annotations

import asyncio
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.object_store import ObjectStore
from app.adapters.pdf_writer import render_pdf
from app.codes.billing_codes import Code
from app.core.config import get_settings
from app.models import Practice, Signature, SigningEvent
from app.services.certificate_layout import CertificateFacts, certificate_document
from app.services.defense_record_layout import ANSWER_WORDS
from app.services.sealed_records import APPROVAL_EVENTS, PROVIDER_EVENTS, source_record

__all__ = [
    "CertificateFile",
    "certificate_facts",
    "certificate_files",
    "note_certificates",
    "note_signing_events",
    "verify_url",
]

CertificateFile = tuple[str, bytes]
NOT_FOUND_SUMMARY = (("Record", "Not found"),)


def verify_url(code: str) -> str:
    return f"{get_settings().app_url}/verify?code={code}"


async def note_signing_events(db: AsyncSession, note_id: str) -> list[SigningEvent]:
    rows = await db.scalars(
        select(SigningEvent).where(SigningEvent.note_id == note_id).order_by(SigningEvent.signed_at)
    )
    return list(rows.all())


async def certificate_facts(db: AsyncSession, store: ObjectStore, row: SigningEvent) -> CertificateFacts:
    practice = await db.get_one(Practice, row.practice_id)
    signature = await db.get(Signature, row.signature_id) if row.signature_id else None
    image = await store.get(signature.file_key) if signature is not None else None
    return CertificateFacts(
        code=row.code,
        event=row.event,
        practice_name=practice.name,
        signer_name=row.signer_name,
        signer_title=row.signer_title,
        typed_name=row.typed_name,
        signed_at=row.signed_at,
        ip=row.ip,
        user_agent=row.user_agent,
        statement=row.statement,
        summary=await _summary(db, row),
        image=image,
        source=signature.source if signature is not None else None,
        document_sha256=row.document_sha256,
        content_sha256=row.content_sha256,
        envelope_sha256=row.envelope_sha256,
        seal=f"{row.seal_algorithm} · {row.seal_key_id}",
        verify_url=verify_url(row.code),
    )


async def note_certificates(db: AsyncSession, store: ObjectStore, note_id: str) -> list[CertificateFacts]:
    return [await certificate_facts(db, store, row) for row in await note_signing_events(db, note_id)]


async def certificate_files(certificates: list[CertificateFacts], zone: ZoneInfo) -> list[CertificateFile]:
    files = []
    for facts in certificates:
        content = await asyncio.to_thread(render_pdf, certificate_document(facts, zone))
        files.append((f"certificates/{facts.code}.pdf", content))
    return files


async def _summary(db: AsyncSession, row: SigningEvent) -> tuple[tuple[str, str], ...]:
    record = await source_record(db, row.event, row.record_id)
    if record is None:
        return NOT_FOUND_SUMMARY
    if row.event in APPROVAL_EVENTS:
        return _claim_summary(record)
    if row.event in PROVIDER_EVENTS:
        return _statement_summary(record)
    return (("Agreement version", str(record["signup"].get("agreement_version", ""))),)


def _labels(items: list[dict[str, Any]]) -> str:
    return ", ".join(Code.from_json(item).label() for item in items) or "None"


def _claim_summary(record: dict[str, Any]) -> tuple[tuple[str, str], ...]:
    content = record["content"]
    return (
        ("Claim", _labels(content.get("codes", []))),
        ("Billed", _labels(content.get("billed", []))),
        ("Snapshot", f"Revision {record['revision']}"),
        ("Decisions", str(len(content.get("decisions", [])))),
    )


def _statement_summary(record: dict[str, Any]) -> tuple[tuple[str, str], ...]:
    rows = [("Answer", ANSWER_WORDS.get(record["answer"], record["answer"])), ("Shown and signed", record["shown"])]
    if record.get("comment"):
        rows.append(("Comment", record["comment"]))
    return tuple(rows)
