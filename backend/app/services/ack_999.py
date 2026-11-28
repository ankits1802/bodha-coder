from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from app.codes.x12_codes import ACK_ACCEPTED, ELEMENT_ERRORS, GROUP_ERRORS, SEGMENT_ERRORS, TRANSACTION_ERRORS
from app.services.x12 import Segment, Transaction, X12Invalid, read_segments, read_transactions

__all__ = ["AckReason", "GroupAck", "SetAck", "decoded", "parse_999"]

CLAIM_GROUP = "HC"
SET_CODES = range(2, 7)
GROUP_CODES = range(5, 10)


@dataclass(frozen=True)
class AckReason:
    code: str
    text: str

    def as_json(self) -> dict[str, str]:
        return {"code": self.code, "text": self.text}


@dataclass(frozen=True)
class SetAck:
    control: str
    status: str
    reasons: tuple[AckReason, ...]

    @property
    def accepted(self) -> bool:
        return self.status in ACK_ACCEPTED


@dataclass(frozen=True)
class GroupAck:
    group_control: str
    receiver_id: str
    status: str
    sets: tuple[SetAck, ...]
    reasons: tuple[AckReason, ...]

    @property
    def accepted(self) -> bool:
        return self.status in ACK_ACCEPTED


@dataclass
class _OpenSet:
    control: str
    reasons: list[AckReason] = field(default_factory=list)
    segment: str = ""
    status: str = ""


def decoded(data: bytes) -> str:
    try:
        return data.decode("utf-8-sig").lstrip()
    except UnicodeDecodeError as error:
        raise X12Invalid("the file is not an X12 text file") from error


def parse_999(data: bytes) -> list[GroupAck]:
    text = decoded(data)
    groups = [segment for segment in read_segments(text) if segment.id == "GS"]
    return [_group(transaction, groups) for transaction in read_transactions(text, code="999")]


def _group(transaction: Transaction, groups: Sequence[Segment]) -> GroupAck:
    opener = next((segment for segment in transaction.segments if segment.id == "AK1"), None)
    closer = next((segment for segment in transaction.segments if segment.id == "AK9"), None)
    if opener is None or closer is None:
        raise X12Invalid(f"999 transaction {transaction.control} needs AK1 and AK9")
    if opener.required(1) != CLAIM_GROUP:
        raise X12Invalid(f"999 transaction {transaction.control} acknowledges {opener.get(1)}, not claims")
    start = transaction.segments[0].position
    envelope = max((segment for segment in groups if segment.position < start), key=lambda item: item.position)
    return GroupAck(
        group_control=opener.required(2),
        receiver_id=envelope.get(3),
        status=closer.required(1),
        sets=tuple(_sets(transaction.segments)),
        reasons=tuple(_coded(closer, GROUP_CODES, GROUP_ERRORS, "AK9", "file")),
    )


def _sets(segments: Sequence[Segment]) -> list[SetAck]:
    found: list[SetAck] = []
    current: _OpenSet | None = None
    for segment in segments:
        current = _step(current, segment, found)
    if current is not None:
        raise X12Invalid(f"transaction set {current.control} in the 999 has no IK5")
    return found


def _step(current: _OpenSet | None, segment: Segment, found: list[SetAck]) -> _OpenSet | None:
    if segment.id == "AK2":
        return _OpenSet(segment.required(2))
    if current is None:
        return None
    if segment.id in ("IK3", "IK4"):
        _note_error(current, segment)
        return current
    if segment.id != "IK5":
        return current
    current.status = segment.required(1)
    current.reasons += _coded(segment, SET_CODES, TRANSACTION_ERRORS, "IK5", "transaction")
    found.append(SetAck(current.control, current.status, tuple(current.reasons)))
    return None


def _note_error(current: _OpenSet, segment: Segment) -> None:
    if segment.id == "IK3":
        loop = f" (loop {segment.get(3)})" if segment.get(3) else ""
        current.segment = f"segment {segment.get(1)} {segment.get(2)}{loop}"
        meaning = SEGMENT_ERRORS.get(segment.get(4), f"segment error {segment.get(4)}")
        current.reasons.append(AckReason(f"IK3-{segment.get(4)}", f"{current.segment}: {meaning}"))
        return
    element = segment.parts(1)[0] if segment.parts(1) else "?"
    meaning = ELEMENT_ERRORS.get(segment.get(3), f"element error {segment.get(3)}")
    place = f"element {element} of {current.segment}" if current.segment else f"element {element}"
    current.reasons.append(AckReason(f"IK4-{segment.get(3)}", f"{place}: {meaning}"))


def _coded(segment: Segment, numbers: range, meanings: dict[str, str], name: str, scope: str) -> list[AckReason]:
    return [
        AckReason(f"{name}-{segment.get(number)}", f"{scope}: {meanings.get(segment.get(number), 'error')}")
        for number in numbers
        if segment.get(number)
    ]
