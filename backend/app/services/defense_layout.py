from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from app.adapters.pdf_writer import PdfBlock, PdfDocument, PdfFacts, PdfHeading, PdfPageBreak, PdfTable, PdfText
from app.codes.billing_codes import Code
from app.codes.fees import ClaimEstimate
from app.services.finding import Finding

__all__ = [
    "ADDENDUM_LABEL",
    "CHOICE_LABELS",
    "DecidedFinding",
    "PacketEvent",
    "PacketFacts",
    "PacketRequest",
    "PacketVisit",
    "packet_document",
    "patient_initials",
]

TITLE = "Audit defense packet"
ADDENDUM_LABEL = "Addendum (amendment to the original note)"
NOT_RECORDED = "Not recorded"
KIND_LABELS = {"em": "Visit level", "diagnosis": "Diagnosis", "code_review": "Procedure code", "modifier": "Modifier"}
CHOICE_LABELS = {"accept": "Accepted", "keep": "Kept", "add": "Added", "ask": "Asked the provider", "skip": "Skipped"}
MDM_ELEMENTS = (
    ("problems", "Problems addressed"),
    ("data", "Data reviewed and analysed"),
    ("risk", "Risk of management"),
)
_NAME_PARTS = re.compile(r"[\s,.-]+")


@dataclass(frozen=True)
class PacketEvent:
    at: datetime
    who: str
    what: str


@dataclass(frozen=True)
class PacketRequest:
    sent_at: datetime
    sent_by: str
    channel: str
    status: str
    answers: tuple[tuple[str, str], ...]
    addendum_text: str | None
    signed_at: datetime | None
    provider_label: str


@dataclass(frozen=True)
class DecidedFinding:
    finding: Finding
    choice: str
    decided_by: str | None
    decided_at: datetime | None


@dataclass(frozen=True)
class PacketVisit:
    practice_name: str
    provider_label: str
    provider_npi: str | None
    provider_specialty: str | None
    place: str
    patient_name: str | None
    patient_age: int | None
    patient_sex: str | None
    service_date: date
    visit_type: str


@dataclass(frozen=True)
class PacketFacts:
    zone: ZoneInfo
    visit: PacketVisit
    approved: PacketEvent | None
    claim: tuple[Code, ...]
    billed: tuple[Code, ...]
    estimate: ClaimEstimate | None
    em: Finding | None
    decided: tuple[DecidedFinding, ...]
    checks: tuple[tuple[str, str], ...]
    requests: tuple[PacketRequest, ...]
    history: tuple[PacketEvent, ...]
    analyses: tuple[tuple[str, ...], ...]
    analysis_label: str
    generated: PacketEvent


def patient_initials(name: str | None) -> str:
    parts = [part for part in _NAME_PARTS.split(name or "") if part]
    return "".join(f"{part[0].upper()}." for part in parts) or NOT_RECORDED


def packet_document(facts: PacketFacts) -> PdfDocument:
    blocks: list[PdfBlock] = [*_cover(facts), PdfPageBreak(), *_visit(facts), *_claim(facts), *_em_basis(facts)]
    blocks += [*_decided(facts), *_checks(facts), *_requests(facts), *_history(facts), *_analyses(facts)]
    return PdfDocument(TITLE, f"Bodha Coder · {TITLE} · {facts.visit.practice_name}", tuple(blocks))


def _day(moment: date) -> str:
    return moment.strftime("%d %b %Y")


def _moment(moment: datetime, zone: ZoneInfo) -> str:
    return moment.astimezone(zone).strftime("%d %b %Y %H:%M %Z")


def _cover(facts: PacketFacts) -> list[PdfBlock]:
    approved = facts.approved
    status = f"Approved {_moment(approved.at, facts.zone)} by {approved.who}" if approved else "Not approved"
    rows = (
        ("Practice", facts.visit.practice_name),
        ("Provider", facts.visit.provider_label),
        ("NPI", facts.visit.provider_npi or NOT_RECORDED),
        ("Specialty", facts.visit.provider_specialty or NOT_RECORDED),
        ("Date of service", _day(facts.visit.service_date)),
        ("Place of service", facts.visit.place),
        ("Patient", patient_initials(facts.visit.patient_name)),
        ("Visit type", facts.visit.visit_type),
        ("Claim", status),
        ("Analysis", facts.analysis_label),
        ("Prepared", f"{_moment(facts.generated.at, facts.zone)} by {facts.generated.who}"),
    )
    return [PdfHeading(TITLE, 1), PdfFacts(rows)]


def _visit(facts: PacketFacts) -> list[PdfBlock]:
    rows = (
        ("Patient", facts.visit.patient_name or NOT_RECORDED),
        ("Age", str(facts.visit.patient_age) if facts.visit.patient_age is not None else NOT_RECORDED),
        ("Sex", facts.visit.patient_sex or NOT_RECORDED),
        ("Date of service", _day(facts.visit.service_date)),
        ("Place of service", facts.visit.place),
        ("Provider", facts.visit.provider_label),
    )
    return [PdfHeading("Patient and visit"), PdfFacts(rows)]


def _code_rows(codes: tuple[Code, ...], estimate: ClaimEstimate | None) -> tuple[tuple[str, ...], ...]:
    amounts = {line.code.label(): line.amount for line in estimate.lines} if estimate else {}
    rows = []
    for code in codes:
        amount = amounts.get(code.label())
        priced = f"${amount:,.2f}" if amount is not None else "—"
        row = (code.code, code.type, " ".join(code.modifiers) or "—", str(code.units) if code.type == "CPT" else "—")
        rows.append((*row, priced) if estimate else row)
    return tuple(rows)


def _claim(facts: PacketFacts) -> list[PdfBlock]:
    columns = ("Code", "Type", "Modifiers", "Units")
    title = "Final claim" if facts.approved else "Claim as decided, not approved"
    blocks: list[PdfBlock] = [PdfHeading(title)]
    if facts.estimate is not None:
        blocks.append(PdfTable((*columns, "Est. Medicare national"), _code_rows(facts.claim, facts.estimate)))
        setting = facts.estimate.setting.replace("_", "-")
        total = f"${facts.estimate.total:,.2f}"
        blocks.append(
            PdfText(f"CMS physician fee schedule {facts.estimate.release}, {setting} rate: {total}", "secondary")
        )
    else:
        blocks.append(PdfTable(columns, _code_rows(facts.claim, None)))
    return [*blocks, PdfHeading("Billed codes", 3), PdfTable(columns, _code_rows(facts.billed, None))]


def _quotes(evidence: tuple[str, ...]) -> list[PdfBlock]:
    return [PdfText(f"“{quote}”", "quote") for quote in evidence if quote.strip()]


def _em_basis(facts: PacketFacts) -> list[PdfBlock]:
    em = facts.em
    if em is None:
        return [PdfHeading("E/M level basis"), PdfText("No E/M review in the current analysis.", "secondary")]
    detail: dict[str, Any] = em.detail
    rows = [
        ("Billed", em.code_before or "—"),
        ("Supported", em.code_after or "—"),
        ("Basis", "Time" if detail.get("basis") == "Time" else "Medical decision making"),
        ("MDM level", detail.get("mdm_level") or "—"),
    ]
    elements = detail.get("mdm_elements") or {}
    for key, label in MDM_ELEMENTS:
        element = elements.get(key) or {}
        rows.append((label, " · ".join(str(part) for part in (element.get("level"), element.get("reason")) if part)))
    if detail.get("time_minutes") is not None:
        rows.append(("Documented time", f"{detail['time_minutes']} minutes"))
    blocks: list[PdfBlock] = [
        PdfHeading("E/M level basis"),
        PdfFacts(tuple((label, value or "—") for label, value in rows)),
    ]
    if em.reasoning:
        blocks += [PdfHeading("Justification", 3), PdfText(em.reasoning)]
    return [*blocks, *([PdfHeading("Evidence", 3)] if em.evidence else []), *_quotes(em.evidence)]


def _decided(facts: PacketFacts) -> list[PdfBlock]:
    blocks: list[PdfBlock] = [PdfHeading("Suggestions accepted or kept")]
    if not facts.decided:
        return [*blocks, PdfText("No suggestion was accepted or kept.", "secondary")]
    for item in facts.decided:
        finding = item.finding
        change = " → ".join(code for code in (finding.code_before, finding.code_after) if code)
        when = f" by {item.decided_by}, {_moment(item.decided_at, facts.zone)}" if item.decided_at else " by default"
        line = " · ".join(part for part in (KIND_LABELS.get(finding.kind, finding.kind), change) if part)
        blocks += [
            PdfHeading(finding.title or line, 3),
            PdfText(f"{line} · {CHOICE_LABELS[item.choice]}{when}", "secondary"),
        ]
        blocks += [PdfText(finding.reasoning)] if finding.reasoning else []
        blocks += _quotes(finding.evidence)
    return blocks


def _checks(facts: PacketFacts) -> list[PdfBlock]:
    return [PdfHeading("Code-set checks"), PdfFacts(facts.checks)]


def _requests(facts: PacketFacts) -> list[PdfBlock]:
    blocks: list[PdfBlock] = [PdfHeading("Provider questions")]
    if not facts.requests:
        return [*blocks, PdfText("No questions were sent to the provider.", "secondary")]
    for request in facts.requests:
        sent = f"Sent {_moment(request.sent_at, facts.zone)} by {request.sent_by} · {request.channel}"
        blocks += [
            PdfHeading(f"{request.provider_label} · {request.status.capitalize()}", 3),
            PdfText(sent, "secondary"),
        ]
        blocks.append(PdfTable(("Question", "Answer"), request.answers, (3, 2)))
        if request.addendum_text and request.signed_at:
            signed = f"{ADDENDUM_LABEL} · signed {_moment(request.signed_at, facts.zone)} by {request.provider_label}"
            blocks += [PdfHeading(signed, 3), PdfText(request.addendum_text, "quote")]
    return blocks


def _history(facts: PacketFacts) -> list[PdfBlock]:
    rows = tuple((_moment(event.at, facts.zone), event.who, event.what) for event in facts.history)
    return [PdfHeading("Decision history"), PdfTable(("When", "Who", "What"), rows, (2, 2, 5))]


def _analyses(facts: PacketFacts) -> list[PdfBlock]:
    columns = ("Run", "Reason", "Status", "Model", "Prompt version", "Finished")
    return [PdfHeading("Analysis runs"), PdfTable(columns, facts.analyses, (2, 2, 2, 3, 2, 3))]
