from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from app.codes.x12_codes import ACCEPTED_CATEGORIES, REJECTED_CATEGORIES, STATUS_CATEGORIES
from app.services.ack_999 import AckReason, decoded
from app.services.x12 import Segment, Transaction, X12Invalid, read_transactions

__all__ = ["ACCEPTED", "PENDING", "REJECTED", "BatchStatus", "ClaimStatus", "StatusLine", "outcome_of", "parse_277ca"]

ACCEPTED, REJECTED, PENDING = "accepted", "rejected", "pending"
RECEIVER_LEVEL, PATIENT_LEVEL = "21", "PT"
REJECT_ACTION = "U"
STATUS_COMPOSITES = (1, 10, 11)
MESSAGE_ELEMENT = 12
REFERENCE_LIMIT = 50


@dataclass(frozen=True)
class StatusLine:
    category: str
    status: str
    entity: str
    action: str
    message: str

    def reason(self) -> AckReason:
        code = ":".join(part for part in (self.category, self.status, self.entity) if part)
        meaning = STATUS_CATEGORIES.get(self.category, f"status category {self.category}")
        detail = f" (status {self.status})" if self.status else ""
        said = f": {self.message.lower()}" if self.message else ""
        return AckReason(code, f"{meaning}{detail}{said}")


@dataclass(frozen=True)
class ClaimStatus:
    claim_ref: str
    statuses: tuple[StatusLine, ...]
    payer_claim_number: str | None

    @property
    def outcome(self) -> str:
        return outcome_of(self.statuses)


@dataclass(frozen=True)
class BatchStatus:
    batch_ref: str | None
    statuses: tuple[StatusLine, ...]
    claims: tuple[ClaimStatus, ...]

    @property
    def outcome(self) -> str:
        return outcome_of(self.statuses)


def outcome_of(statuses: Sequence[StatusLine]) -> str:
    if any(line.category in REJECTED_CATEGORIES or line.action == REJECT_ACTION for line in statuses):
        return REJECTED
    if any(line.category in ACCEPTED_CATEGORIES for line in statuses):
        return ACCEPTED
    return PENDING


def parse_277ca(data: bytes) -> list[BatchStatus]:
    found: list[BatchStatus] = []
    for transaction in read_transactions(decoded(data), code="277"):
        found += _batches(transaction)
    return found


def _batches(transaction: Transaction) -> list[BatchStatus]:
    blocks = _levels(transaction.segments[1:-1])
    batches: list[tuple[list[Segment], list[ClaimStatus]]] = []
    for block in blocks:
        level = block[0].get(3)
        if level == RECEIVER_LEVEL:
            batches.append((block, []))
            continue
        if level != PATIENT_LEVEL:
            continue
        if not batches:
            raise X12Invalid(f"a claim at segment {block[0].position} comes before any information receiver")
        batches[-1][1].append(_claim(block))
    if not batches:
        raise X12Invalid(f"277 transaction {transaction.control} has no information receiver level")
    return [BatchStatus(_trace(block), _statuses(block), tuple(claims)) for block, claims in batches]


def _claim(block: list[Segment]) -> ClaimStatus:
    reference = _trace(block)
    if reference is None:
        raise X12Invalid(f"the claim at segment {block[0].position} has no TRN*2 claim reference")
    payer_number = next((item.get(2) for item in block if item.id == "REF" and item.get(1) == "1K"), "")
    statuses = _statuses(block)
    if not statuses:
        raise X12Invalid(f"the claim at segment {block[0].position} has no STC status")
    return ClaimStatus(reference, statuses, payer_number[:REFERENCE_LIMIT] or None)


def _levels(segments: Sequence[Segment]) -> list[list[Segment]]:
    blocks: list[list[Segment]] = []
    for segment in segments:
        if segment.id == "HL":
            blocks.append([segment])
        elif blocks:
            blocks[-1].append(segment)
    return blocks


def _trace(block: list[Segment]) -> str | None:
    found = next((item for item in block if item.id == "TRN" and item.get(1) == "2"), None)
    return (found.get(2) or None) if found else None


def _statuses(block: list[Segment]) -> tuple[StatusLine, ...]:
    lines: list[StatusLine] = []
    for item in block:
        if item.id != "STC":
            continue
        for number in STATUS_COMPOSITES:
            parts = item.parts(number)
            if parts and parts[0]:
                padded = (*parts, "", "")
                message = item.get(MESSAGE_ELEMENT) if number == 1 else ""
                lines.append(StatusLine(padded[0], padded[1], padded[2], item.get(3), message))
    return tuple(lines)
