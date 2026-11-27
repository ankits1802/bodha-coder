from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from app.adapters.pdf_writer import PdfBlock, PdfHeading, PdfTable, PdfText
from app.services.finding import Finding

__all__ = [
    "ADDENDUM_LABEL",
    "CHOICE_LABELS",
    "PacketAttestation",
    "PacketComment",
    "PacketRecords",
    "PacketReview",
    "PacketRow",
    "PacketText",
    "packet_moment",
    "record_blocks",
]

ADDENDUM_LABEL = "Addendum (amendment to the original note)"
NONE_TEXT = {
    "not_followed": "Every suggestion was followed.",
    "earlier": "No earlier run.",
    "compliance": "Never flagged for compliance.",
    "snapshots": "Not approved yet.",
    "exports": "Not exported yet.",
    "attestations": "No provider statement.",
    "comments": "No comments.",
}
CHOICE_LABELS = {"accept": "Accepted", "keep": "Kept", "add": "Added", "ask": "Asked the provider", "skip": "Skipped"}
PURPOSE_WORDS = {"questions": "Addendum answers", "level_change": "Visit level change"}
ANSWER_WORDS = {"signed": "Signed", "confirm": "Confirmed", "disagree": "Disagreed"}


@dataclass(frozen=True)
class PacketText:
    revision: int
    source: str
    text: str


@dataclass(frozen=True)
class PacketReview:
    finding: Finding
    choice: str
    decided_by: str | None
    decided_at: datetime | None
    reason: str | None


@dataclass(frozen=True)
class PacketRow:
    at: datetime
    cells: tuple[str, ...]


@dataclass(frozen=True)
class PacketAttestation:
    at: datetime
    provider: str
    purpose: str
    answer: str
    wording: str
    shown: str
    comment: str | None
    ip: str | None


@dataclass(frozen=True)
class PacketComment:
    at: datetime
    author: str
    on: str
    body: str
    removed: tuple[str, datetime] | None


@dataclass(frozen=True)
class PacketRecords:
    texts: tuple[PacketText, ...]
    not_followed: tuple[PacketReview, ...]
    earlier: tuple[tuple[str, ...], ...]
    compliance: tuple[PacketRow, ...]
    snapshots: tuple[PacketRow, ...]
    exports: tuple[PacketRow, ...]
    attestations: tuple[PacketAttestation, ...]
    comments: tuple[PacketComment, ...]
    flag_reason: str | None


def record_blocks(records: PacketRecords, zone: ZoneInfo) -> list[PdfBlock]:
    return [
        *_texts(records),
        *_not_followed(records, zone),
        *_earlier(records),
        *_compliance(records, zone),
        *_snapshots(records, zone),
        *_exports(records, zone),
        *_attestations(records, zone),
        *_comments(records, zone),
    ]


def packet_moment(moment: datetime, zone: ZoneInfo) -> str:
    return moment.astimezone(zone).strftime("%d %b %Y %H:%M %Z")


def _empty(title: str, key: str) -> list[PdfBlock]:
    return [PdfHeading(title), PdfText(NONE_TEXT[key], "secondary")]


def _texts(records: PacketRecords) -> list[PdfBlock]:
    blocks: list[PdfBlock] = [PdfHeading("Note text")]
    for text in records.texts:
        label = f"Document, revision {text.revision}" if text.source == "document" else ADDENDUM_LABEL
        blocks += [PdfHeading(label, 3), PdfText(text.text)]
    return blocks


def _not_followed(records: PacketRecords, zone: ZoneInfo) -> list[PdfBlock]:
    title = "Suggestions not followed"
    if not records.not_followed:
        return _empty(title, "not_followed")
    blocks: list[PdfBlock] = [PdfHeading(title)]
    for item in records.not_followed:
        finding = item.finding
        change = " → ".join(code for code in (finding.code_before, finding.code_after) if code)
        when = f" by {item.decided_by}, {packet_moment(item.decided_at, zone)}" if item.decided_at else " by default"
        blocks += [
            PdfHeading(" · ".join(part for part in (finding.title, change) if part), 3),
            PdfText(f"{CHOICE_LABELS.get(item.choice, item.choice)}{when}", "secondary"),
            PdfText(f"Reason: {item.reason}" if item.reason else "Reason: not recorded"),
        ]
    return blocks


def _earlier(records: PacketRecords) -> list[PdfBlock]:
    title = "Suggestions from earlier runs"
    if not records.earlier:
        return _empty(title, "earlier")
    columns = ("Run", "Kind", "Action", "Change", "Suggestion")
    return [PdfHeading(title), PdfTable(columns, records.earlier, (1, 2, 2, 2, 5))]


def _rows(rows: tuple[PacketRow, ...], zone: ZoneInfo) -> tuple[tuple[str, ...], ...]:
    return tuple((packet_moment(row.at, zone), *row.cells) for row in rows)


def _compliance(records: PacketRecords, zone: ZoneInfo) -> list[PdfBlock]:
    title = "Flag and compliance reasons"
    if not records.compliance and not records.flag_reason:
        return _empty(title, "compliance")
    blocks: list[PdfBlock] = [PdfHeading(title)]
    if records.flag_reason:
        blocks.append(PdfText(f"Open flag: {records.flag_reason}"))
    columns = ("When", "Who", "What", "Reason")
    return [*blocks, PdfTable(columns, _rows(records.compliance, zone), (2, 2, 2, 4))]


def _snapshots(records: PacketRecords, zone: ZoneInfo) -> list[PdfBlock]:
    title = "Approved claim snapshots"
    if not records.snapshots:
        return _empty(title, "snapshots")
    columns = ("Approved", "Revision", "Approver", "Codes", "Model · prompt", "PDF SHA-256")
    return [PdfHeading(title), PdfTable(columns, _rows(records.snapshots, zone), (2, 1, 2, 3, 2, 2))]


def _exports(records: PacketRecords, zone: ZoneInfo) -> list[PdfBlock]:
    title = "Claim exports"
    if not records.exports:
        return _empty(title, "exports")
    columns = ("When", "Who", "Format", "Visits", "Snapshot", "File SHA-256")
    return [PdfHeading(title), PdfTable(columns, _rows(records.exports, zone), (2, 2, 2, 1, 1, 2))]


def _attestations(records: PacketRecords, zone: ZoneInfo) -> list[PdfBlock]:
    title = "Provider statements"
    if not records.attestations:
        return _empty(title, "attestations")
    blocks: list[PdfBlock] = [PdfHeading(title)]
    for item in records.attestations:
        heading = f"{PURPOSE_WORDS.get(item.purpose, item.purpose)} · {ANSWER_WORDS.get(item.answer, item.answer)}"
        meta = f"{item.provider} · {packet_moment(item.at, zone)} · {item.ip or 'address not recorded'}"
        blocks += [PdfHeading(heading, 3), PdfText(meta, "secondary"), PdfText(f"Confirmed: {item.wording}")]
        blocks.append(PdfText(item.shown, "quote"))
        blocks += [PdfText(f"Comment: {item.comment}")] if item.comment else []
    return blocks


def _comments(records: PacketRecords, zone: ZoneInfo) -> list[PdfBlock]:
    title = "Comments"
    if not records.comments:
        return _empty(title, "comments")
    rows = tuple(
        (
            packet_moment(item.at, zone),
            item.author,
            item.on,
            item.body,
            f"Removed by {item.removed[0]}, {packet_moment(item.removed[1], zone)}" if item.removed else "—",
        )
        for item in records.comments
    )
    return [PdfHeading(title), PdfTable(("When", "Who", "On", "Comment", "Removed"), rows, (2, 2, 2, 5, 2))]
