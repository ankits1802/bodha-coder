from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from app.services.x12 import Segment, Transaction, X12Invalid, read_transactions

__all__ = ["Adjustment", "ClaimPayment", "PaymentAdvice", "ServicePayment", "parse_835"]

AMOUNT = re.compile(r"^-?(\d+(\.\d{0,2})?|\.\d{1,2})$")
X12_DATE = re.compile(r"^\d{8}$")
PRODUCTION_DATE = "405"
SERVICE_DATE = "472"
CLAIM_START = "232"
PATIENT = "QC"
PAYER = "PR"
PAYER_REFERENCE = "2U"
CAS_TRIPLES = range(2, 20, 3)
PLB_AMOUNTS = range(4, 15, 2)


@dataclass(frozen=True)
class Adjustment:
    group: str
    reason: str
    cents: int

    def as_json(self) -> dict[str, Any]:
        return {"group": self.group, "reason": self.reason, "cents": self.cents}

    @classmethod
    def from_json(cls, value: dict[str, Any]) -> Adjustment:
        return cls(str(value["group"]), str(value["reason"]), int(value["cents"]))


@dataclass(frozen=True)
class ServicePayment:
    billed_code: str | None
    paid_code: str | None
    billed_cents: int
    paid_cents: int
    service_date: date | None
    adjustments: tuple[Adjustment, ...]


@dataclass(frozen=True)
class ClaimPayment:
    claim_ref: str
    status: str
    billed_cents: int
    paid_cents: int
    filing_indicator: str | None
    payer_claim_number: str | None
    patient_name: str | None
    member_id: str | None
    service_date: date | None
    adjustments: tuple[Adjustment, ...]
    lines: tuple[ServicePayment, ...]

    def payments(self) -> tuple[ServicePayment, ...]:
        if self.lines:
            return self.lines
        return (ServicePayment(None, None, self.billed_cents, self.paid_cents, self.service_date, self.adjustments),)


@dataclass(frozen=True)
class PaymentAdvice:
    payer_name: str | None
    payer_id: str | None
    paid_on: date
    total_cents: int
    trace_number: str | None
    claims: tuple[ClaimPayment, ...]


def parse_835(data: bytes) -> list[PaymentAdvice]:
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise X12Invalid("the file is not an X12 text file") from error
    return [_advice(transaction) for transaction in read_transactions(text.lstrip(), code="835")]


def _advice(transaction: Transaction) -> PaymentAdvice:
    header, chunks, summary = _sections(transaction.segments[1:-1])
    bpr = _first(header, "BPR")
    if bpr is None:
        raise X12Invalid(f"transaction {transaction.control} has no BPR segment")
    payer = next((item for item in header if item.id == "N1" and item.get(1) == PAYER), None)
    reference = next((item for item in header if item.id == "REF" and item.get(1) == PAYER_REFERENCE), None)
    trace = _first(header, "TRN")
    advice = PaymentAdvice(
        payer_name=(payer.get(2) or None) if payer else None,
        payer_id=(payer.get(4) if payer else "") or (reference.get(2) if reference else "") or None,
        paid_on=_paid_on(bpr, header, transaction.control),
        total_cents=_cents(bpr, 2),
        trace_number=(trace.get(2) or None) if trace else None,
        claims=tuple(_claim(chunk) for chunk in chunks),
    )
    _check_balance(advice, summary, transaction.control)
    return advice


def _sections(segments: Sequence[Segment]) -> tuple[list[Segment], list[list[Segment]], list[Segment]]:
    header: list[Segment] = []
    claims: list[list[Segment]] = []
    summary: list[Segment] = []
    current: list[Segment] | None = None
    for segment in segments:
        if segment.id == "CLP":
            current = [segment]
            claims.append(current)
            continue
        if segment.id in ("LX", "PLB"):
            current = None
            (summary if segment.id == "PLB" else header).append(segment)
            continue
        (header if current is None else current).append(segment)
    return header, claims, summary


def _paid_on(bpr: Segment, header: Sequence[Segment], control: str) -> date:
    if bpr.get(16):
        return _date(bpr, 16)
    produced = _dated(header, PRODUCTION_DATE)
    if produced is None:
        raise X12Invalid(f"transaction {control} has no payment date (BPR16) or production date (DTM*405)")
    return produced


def _claim(chunk: list[Segment]) -> ClaimPayment:
    clp = chunk[0]
    claim_part, line_chunks = _split_lines(chunk[1:])
    patient = next((item for item in claim_part if item.id == "NM1" and item.get(1) == PATIENT), None)
    return ClaimPayment(
        claim_ref=clp.required(1),
        status=clp.required(2),
        billed_cents=_cents(clp, 3),
        paid_cents=_cents(clp, 4),
        filing_indicator=clp.get(6).upper() or None,
        payer_claim_number=clp.get(7) or None,
        patient_name=_person(patient),
        member_id=(patient.get(9) or None) if patient else None,
        service_date=_dated(claim_part, CLAIM_START),
        adjustments=_adjustments(claim_part),
        lines=tuple(_line(line) for line in line_chunks),
    )


def _split_lines(segments: list[Segment]) -> tuple[list[Segment], list[list[Segment]]]:
    claim_part: list[Segment] = []
    lines: list[list[Segment]] = []
    for segment in segments:
        if segment.id == "SVC":
            lines.append([segment])
        elif lines:
            lines[-1].append(segment)
        else:
            claim_part.append(segment)
    return claim_part, lines


def _line(chunk: list[Segment]) -> ServicePayment:
    svc = chunk[0]
    paid_code = _procedure(svc, 1)
    line = ServicePayment(
        billed_code=_procedure(svc, 6) or paid_code,
        paid_code=paid_code,
        billed_cents=_cents(svc, 2),
        paid_cents=_cents(svc, 3),
        service_date=_dated(chunk[1:], SERVICE_DATE),
        adjustments=_adjustments(chunk[1:]),
    )
    adjusted = sum(item.cents for item in line.adjustments)
    if line.billed_cents - adjusted != line.paid_cents:
        raise X12Invalid(f"the service line at segment {svc.position} does not balance (SVC02 - CAS != SVC03)")
    return line


def _procedure(svc: Segment, number: int) -> str | None:
    parts = svc.parts(number)
    if not parts and number == 1:
        raise X12Invalid(f"SVC01 is missing in segment {svc.position}")
    if not parts:
        return None
    if len(parts) < 2 or not parts[1]:
        raise X12Invalid(f"SVC{number:02d} in segment {svc.position} needs a qualifier and a code")
    return parts[1].upper()[:16]


def _adjustments(segments: Sequence[Segment]) -> tuple[Adjustment, ...]:
    found: list[Adjustment] = []
    for segment in segments:
        if segment.id == "CAS":
            found += _cas(segment)
    return tuple(found)


def _cas(segment: Segment) -> list[Adjustment]:
    group = segment.required(1).upper()
    items = [
        Adjustment(group, segment.get(start), _cents(segment, start + 1)) for start in CAS_TRIPLES if segment.get(start)
    ]
    if not items:
        raise X12Invalid(f"CAS in segment {segment.position} has no adjustment reason")
    return items


def _check_balance(advice: PaymentAdvice, summary: Sequence[Segment], control: str) -> None:
    provider_adjustments = sum(_cents(item, number) for item in summary for number in PLB_AMOUNTS if item.get(number))
    paid = sum(claim.paid_cents for claim in advice.claims)
    if paid - provider_adjustments != advice.total_cents:
        raise X12Invalid(f"transaction {control} does not balance: claims paid minus PLB differs from BPR02")


def _person(segment: Segment | None) -> str | None:
    if segment is None:
        return None
    name = " ".join(part for part in (segment.get(4), segment.get(5), segment.get(3)) if part)
    return name.title()[:200] or None


def _first(segments: Sequence[Segment], name: str) -> Segment | None:
    return next((item for item in segments if item.id == name), None)


def _dated(segments: Sequence[Segment], qualifier: str) -> date | None:
    found = next((item for item in segments if item.id == "DTM" and item.get(1) == qualifier), None)
    return _date(found, 2) if found else None


def _date(segment: Segment, number: int) -> date:
    text = segment.required(number)
    try:
        if X12_DATE.fullmatch(text) is None:
            raise ValueError(text)
        return datetime.strptime(text, "%Y%m%d").date()
    except ValueError as error:
        raise X12Invalid(f"{segment.id}{number:02d} {text} is not a date (CCYYMMDD)") from error


def _cents(segment: Segment, number: int) -> int:
    text = segment.required(number)
    if AMOUNT.fullmatch(text) is None:
        raise X12Invalid(f"{segment.id}{number:02d} {text} is not an amount")
    return int(Decimal(text) * 100)
