from __future__ import annotations

import re
from dataclasses import dataclass

from app.core.errors import Invalid

__all__ = ["Segment", "Transaction", "X12Invalid", "first_transaction_code", "read_segments", "read_transactions"]

ISA_LENGTH = 106
ISA_ELEMENTS = 16
ELEMENT_AT, COMPONENT_AT, TERMINATOR_AT = 3, 104, 105
SEGMENT_ID = re.compile(r"^[A-Z][A-Z0-9]{1,2}$")


class X12Invalid(Invalid):
    pass


@dataclass(frozen=True)
class Separators:
    element: str
    component: str
    segment: str


@dataclass(frozen=True)
class Segment:
    id: str
    elements: tuple[str, ...]
    component: str
    position: int

    def get(self, number: int) -> str:
        return self.elements[number - 1].strip() if 0 < number <= len(self.elements) else ""

    def required(self, number: int) -> str:
        value = self.get(number)
        if not value:
            raise X12Invalid(f"{self.id}{number:02d} is missing in segment {self.position}")
        return value

    def parts(self, number: int) -> tuple[str, ...]:
        value = self.get(number)
        return tuple(part.strip() for part in value.split(self.component)) if value else ()


@dataclass(frozen=True)
class Transaction:
    code: str
    control: str
    segments: tuple[Segment, ...]


def read_transactions(text: str, *, code: str) -> list[Transaction]:
    separators = _separators(text)
    segments = _segments(text, separators)
    if len(segments) < 2 or segments[0].id != "ISA" or segments[-1].id != "IEA":
        raise X12Invalid("the file must start with ISA and end with IEA")
    groups = _envelopes(segments[1:-1], "GS", "GE")
    _check_trailer(segments[-1], count=len(groups), control=segments[0].required(13))
    found: list[Transaction] = []
    for group in groups:
        found += _group_transactions(group, code)
    if not found:
        raise X12Invalid("the file holds no transaction")
    return found


def read_segments(text: str) -> list[Segment]:
    return _segments(text, _separators(text))


def first_transaction_code(text: str) -> str:
    opener = next((segment for segment in read_segments(text) if segment.id == "ST"), None)
    if opener is None:
        raise X12Invalid("the file holds no transaction")
    return opener.required(1)


def _separators(text: str) -> Separators:
    if len(text) < ISA_LENGTH or not text.startswith("ISA"):
        raise X12Invalid("the file does not start with an ISA segment")
    chosen = Separators(text[ELEMENT_AT], text[COMPONENT_AT], text[TERMINATOR_AT])
    marks = (chosen.element, chosen.component, chosen.segment)
    if len(set(marks)) != len(marks) or any(mark.isalnum() or mark == " " for mark in marks):
        raise X12Invalid("the ISA segment does not declare three distinct separators")
    if text[:COMPONENT_AT].count(chosen.element) != ISA_ELEMENTS:
        raise X12Invalid(f"the ISA segment must have {ISA_ELEMENTS} elements of fixed width")
    return chosen


def _segments(text: str, separators: Separators) -> list[Segment]:
    found: list[Segment] = []
    for raw in text.split(separators.segment):
        body = raw.strip()
        if not body:
            continue
        name, *elements = body.split(separators.element)
        if SEGMENT_ID.fullmatch(name) is None:
            raise X12Invalid(f"segment {len(found) + 1} has no valid segment id")
        found.append(Segment(name, tuple(elements), separators.component, len(found) + 1))
    return found


def _group_transactions(group: list[Segment], code: str) -> list[Transaction]:
    sets = _envelopes(group[1:-1], "ST", "SE")
    _check_trailer(group[-1], count=len(sets), control=group[0].required(6))
    found: list[Transaction] = []
    for body in sets:
        opener = body[0]
        _check_trailer(body[-1], count=len(body), control=opener.required(2))
        if opener.required(1) != code:
            raise X12Invalid(f"transaction {opener.get(2)} is a {opener.get(1)}, not an {code}")
        found.append(Transaction(code, opener.get(2), tuple(body)))
    return found


def _envelopes(segments: list[Segment], opener: str, closer: str) -> list[list[Segment]]:
    found: list[list[Segment]] = []
    current: list[Segment] | None = None
    for segment in segments:
        if current is None:
            if segment.id != opener:
                raise X12Invalid(f"expected {opener} at segment {segment.position}, found {segment.id}")
            current = [segment]
            continue
        current.append(segment)
        if segment.id == closer:
            found.append(current)
            current = None
        elif segment.id == opener:
            raise X12Invalid(f"{opener} at segment {segment.position} comes before the previous {closer}")
    if current is not None:
        raise X12Invalid(f"{opener} at segment {current[0].position} has no {closer}")
    return found


def _check_trailer(trailer: Segment, *, count: int, control: str) -> None:
    if trailer.required(2) != control:
        raise X12Invalid(f"{trailer.id} control number {trailer.get(2)} does not match {control}")
    stated = trailer.required(1)
    if not stated.isdigit() or int(stated) != count:
        raise X12Invalid(f"{trailer.id} counts {stated} but there are {count}")
