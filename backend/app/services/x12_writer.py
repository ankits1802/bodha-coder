from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

__all__ = [
    "COMPONENT",
    "ELEMENT",
    "TERMINATOR",
    "Interchange",
    "amount",
    "composite",
    "segment",
    "text",
    "write_interchange",
]

ELEMENT, COMPONENT, REPETITION, TERMINATOR = "*", ":", "^", "~"
RESERVED = frozenset(ELEMENT + REPETITION + TERMINATOR + "\r\n")
UNSAFE = re.compile(r"[^A-Z0-9 &'(),./#-]")
SPACES = re.compile(r"\s+")
ISA_ID_WIDTH = 15
EMPTY_AUTHORIZATION = " " * 10
INTERCHANGE_VERSION = "00501"
NO_INTERCHANGE_ACK = "0"
MAX_CONTROL = 999_999_999
ST_CONTROL_WIDTH = 4


@dataclass(frozen=True)
class Interchange:
    sender_qualifier: str
    sender_id: str
    receiver_qualifier: str
    receiver_id: str
    usage: str
    control_number: int
    created: datetime
    functional_id: str
    transaction_code: str
    version: str


def text(value: str, limit: int) -> str:
    cleaned = SPACES.sub(" ", UNSAFE.sub(" ", value.upper())).strip()
    return cleaned[:limit].rstrip()


def amount(cents: int) -> str:
    if cents < 0:
        raise ValueError(f"an amount cannot be negative ({cents} cents)")
    dollars, rest = divmod(cents, 100)
    return str(dollars) if rest == 0 else f"{dollars}.{rest:02d}".rstrip("0")


def composite(*parts: str) -> str:
    for part in parts:
        if COMPONENT in part or RESERVED & set(part):
            raise ValueError(f"a component holds a separator: {part!r}")
    return COMPONENT.join(_trimmed(parts))


def segment(name: str, *elements: str) -> str:
    for element in elements:
        if RESERVED & set(element):
            raise ValueError(f"an element of {name} holds a separator: {element!r}")
    return ELEMENT.join([name, *_trimmed(elements)])


def write_interchange(interchange: Interchange, body: Sequence[str]) -> str:
    control = interchange.control_number
    if not 0 < control <= MAX_CONTROL:
        raise ValueError(f"control number {control} is outside 1 to {MAX_CONTROL}")
    made = interchange.created
    st_control = str(control).zfill(ST_CONTROL_WIDTH)
    segments = [
        _isa(interchange),
        segment(
            "GS",
            interchange.functional_id,
            interchange.sender_id,
            interchange.receiver_id,
            made.strftime("%Y%m%d"),
            made.strftime("%H%M"),
            str(control),
            "X",
            interchange.version,
        ),
        segment("ST", interchange.transaction_code, st_control, interchange.version),
        *body,
        segment("SE", str(len(body) + 2), st_control),
        segment("GE", "1", str(control)),
        segment("IEA", "1", f"{control:09d}"),
    ]
    return TERMINATOR.join(segments) + TERMINATOR


def _isa(interchange: Interchange) -> str:
    for identifier in (interchange.sender_id, interchange.receiver_id):
        if not identifier or len(identifier) > ISA_ID_WIDTH or identifier != identifier.strip():
            raise ValueError(f"interchange id {identifier!r} must be 1 to {ISA_ID_WIDTH} characters")
    made = interchange.created
    elements = (
        "00",
        EMPTY_AUTHORIZATION,
        "00",
        EMPTY_AUTHORIZATION,
        interchange.sender_qualifier,
        interchange.sender_id.ljust(ISA_ID_WIDTH),
        interchange.receiver_qualifier,
        interchange.receiver_id.ljust(ISA_ID_WIDTH),
        made.strftime("%y%m%d"),
        made.strftime("%H%M"),
        REPETITION,
        INTERCHANGE_VERSION,
        f"{interchange.control_number:09d}",
        NO_INTERCHANGE_ACK,
        interchange.usage,
        COMPONENT,
    )
    return ELEMENT.join(["ISA", *elements])


def _trimmed(values: Sequence[str]) -> list[str]:
    kept = list(values)
    while kept and not kept[-1]:
        kept.pop()
    return kept
