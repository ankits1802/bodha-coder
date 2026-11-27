from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from app.adapters.pdf_writer import PdfBlock, PdfDocument, PdfFacts, PdfHeading, PdfImage, PdfText
from app.services.defense_record_layout import packet_moment

__all__ = ["CERTIFICATE_TITLE", "EVENT_LABELS", "CertificateFacts", "certificate_blocks", "certificate_document"]

CERTIFICATE_TITLE = "Certificate of review"
NOT_RECORDED = "Not recorded"
EVENT_LABELS = {
    "approval": "Claim approved",
    "compliance_decision": "Compliance decision",
    "provider_addendum": "Provider addendum signed",
    "provider_level_change": "Provider visit level statement",
    "agreement": "Practice agreement accepted",
}
SOURCE_LABELS = {"drawn": "Drawn by hand", "typed": "Adopted by typing the name", "uploaded": "Photo of a signature"}


@dataclass(frozen=True)
class CertificateFacts:
    code: str
    event: str
    practice_name: str
    signer_name: str
    signer_title: str
    typed_name: str
    signed_at: datetime
    ip: str | None
    user_agent: str | None
    statement: str
    summary: tuple[tuple[str, str], ...]
    image: bytes | None
    source: str | None
    document_sha256: str | None
    content_sha256: str
    envelope_sha256: str
    seal: str
    verify_url: str


def certificate_blocks(facts: CertificateFacts, zone: ZoneInfo) -> list[PdfBlock]:
    signer = (
        ("Event", EVENT_LABELS.get(facts.event, facts.event)),
        ("Practice", facts.practice_name),
        ("Signed by", f"{facts.signer_name} ({facts.signer_title})"),
        ("Typed name", facts.typed_name),
        ("Signed", packet_moment(facts.signed_at, zone)),
        ("IP address", facts.ip or NOT_RECORDED),
        ("Device", facts.user_agent or NOT_RECORDED),
    )
    blocks: list[PdfBlock] = [PdfHeading(CERTIFICATE_TITLE, 1), PdfFacts(signer), PdfText(facts.statement, "quote")]
    if facts.summary:
        blocks += [PdfHeading("Signed content"), PdfFacts(facts.summary)]
    blocks += [PdfHeading("Signature"), *_signature(facts), PdfHeading("Digital fingerprint"), PdfFacts(_prints(facts))]
    return blocks


def certificate_document(facts: CertificateFacts, zone: ZoneInfo) -> PdfDocument:
    footer = f"Bodha Assure · {CERTIFICATE_TITLE} · {facts.code}"
    return PdfDocument(CERTIFICATE_TITLE, footer, tuple(certificate_blocks(facts, zone)))


def _signature(facts: CertificateFacts) -> list[PdfBlock]:
    if facts.image is None:
        return [PdfText(f"Accepted by typed name: {facts.typed_name}", "secondary")]
    return [PdfImage(facts.image), PdfText(SOURCE_LABELS.get(facts.source or "", NOT_RECORDED), "secondary")]


def _prints(facts: CertificateFacts) -> tuple[tuple[str, str], ...]:
    return (
        ("Document SHA-256", facts.document_sha256 or "No document"),
        ("Record SHA-256", facts.content_sha256),
        ("Envelope SHA-256", facts.envelope_sha256),
        ("Seal", facts.seal),
        ("Verification code", facts.code),
        ("Verify at", facts.verify_url),
    )
