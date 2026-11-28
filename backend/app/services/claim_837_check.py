from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from datetime import datetime
from decimal import Decimal

from app.codes.billing_codes import CPT_PATTERN, MODIFIER_PATTERN
from app.codes.credentials import LICENSE_STATES, is_taxonomy_code
from app.codes.icd import is_icd_shaped
from app.codes.npi import is_valid_npi
from app.codes.x12_codes import CLAIM_FILING_CODES
from app.services.x12 import Segment, X12Invalid, read_segments, read_transactions

__all__ = ["check_837p", "problems_837p"]

GUIDE = "005010X222A1"
AMOUNT = re.compile(r"^\d{1,8}(\.\d{1,2})?$")
DIGITS = re.compile(r"^\d+$")
EIN = re.compile(r"^\d{9}$")
ZIP = re.compile(r"^(\d{5}|\d{9})$")
ZIP_NINE = re.compile(r"^\d{9}$")
PHONE = re.compile(r"^\d{10}$")
PLACE = re.compile(r"^\d{2}$")
PARENT_LEVEL = {"20": "", "22": "20", "23": "22"}
PATIENT_RELATIONSHIPS = ("01", "19", "G8")
SEXES = ("F", "M", "U")
FREQUENCIES = ("1", "7", "8")
MAX_DIAGNOSES, MAX_POINTERS, MAX_MODIFIERS, MAX_LINES = 12, 4, 4, 50
SHOWN_PROBLEMS = 10


def check_837p(text: str) -> None:
    problems = problems_837p(text)
    if problems:
        raise X12Invalid("the claim file failed its checks: " + "; ".join(problems[:SHOWN_PROBLEMS]))


def problems_837p(text: str) -> list[str]:
    try:
        segments = read_segments(text)
        transactions = read_transactions(text, code="837")
    except X12Invalid as error:
        return [error.message]
    problems = _envelope(segments[0], segments[1])
    for transaction in transactions:
        problems += _transaction(transaction.segments)
    return problems


def _envelope(isa: Segment, gs: Segment) -> list[str]:
    problems = _expect(isa, {12: "00501", 16: ":"}) + _expect(gs, {1: "HC", 7: "X", 8: GUIDE})
    if isa.get(15) not in ("T", "P"):
        problems.append(f"{_at(isa)}: ISA15 must be T (test) or P (production)")
    return problems + _date(gs, 4) + _length(gs, 2, 2, 15) + _length(gs, 3, 2, 15)


def _transaction(segments: Sequence[Segment]) -> list[str]:
    problems = _expect(segments[0], {3: GUIDE})
    body = list(segments[1:-1])
    start = next((index for index, segment in enumerate(body) if segment.id == "HL"), len(body))
    problems += _header(body[:start])
    blocks = _split(body[start:], "HL")
    if not blocks:
        return [*problems, "the transaction has no billing provider"]
    problems += _hierarchy(blocks)
    for block in blocks:
        problems += _block(block)
    return problems


def _header(header: list[Segment]) -> list[str]:
    if [segment.id for segment in header] != ["BHT", "NM1", "PER", "NM1"]:
        return ["the header must hold BHT, the submitter NM1, its PER and the receiver NM1"]
    bht, submitter, contact, receiver = header
    return (
        _expect(bht, {1: "0019", 2: "00", 6: "CH"})
        + _date(bht, 4)
        + _length(bht, 3, 1, 50)
        + _organization(submitter, "41", "46")
        + _expect(contact, {1: "IC", 3: "TE"})
        + _length(contact, 2, 1, 60)
        + _pattern(contact, 4, PHONE, "a ten-digit phone number")
        + _organization(receiver, "40", "46")
    )


def _hierarchy(blocks: list[list[Segment]]) -> list[str]:
    levels: dict[str, str] = {}
    problems: list[str] = []
    for index, block in enumerate(blocks):
        hl, number = block[0], str(index + 1)
        level, parent = hl.get(3), hl.get(2)
        if hl.get(1) != number:
            problems.append(f"{_at(hl)}: HL01 must be {number}")
        if level not in PARENT_LEVEL:
            problems.append(f"{_at(hl)}: HL03 must be 20, 22 or 23")
            continue
        if levels.get(parent, "") != PARENT_LEVEL[level] or (level == "20" and parent):
            problems.append(f"{_at(hl)}: HL02 must point to an earlier level {PARENT_LEVEL[level] or 'none'}")
        has_child = index + 1 < len(blocks) and blocks[index + 1][0].get(2) == number
        if hl.get(4) != ("1" if has_child else "0"):
            problems.append(f"{_at(hl)}: HL04 must say whether a lower level follows")
        levels[number] = level
    return problems


def _block(block: list[Segment]) -> list[str]:
    level = block[0].get(3)
    claim_at = next((index for index, segment in enumerate(block) if segment.id == "CLM"), len(block))
    head, claim = block[:claim_at], block[claim_at:]
    if level == "20":
        return _billing(head) + ([f"{_at(claim[0])}: a claim cannot sit under a billing provider"] if claim else [])
    if level not in ("22", "23"):
        return []
    problems = _subscriber(head) if level == "22" else _patient(head)
    holds_claim = level == "23" or block[0].get(4) == "0"
    if holds_claim != bool(claim):
        problems.append(f"{_at(block[0])}: a claim belongs under the patient's level")
    return problems + (_claim(claim) if claim else [])


def _billing(head: list[Segment]) -> list[str]:
    problems: list[str] = []
    specialty = _first(head, "PRV")
    if specialty is not None:
        problems += _expect(specialty, {1: "BI", 2: "PXC"}) + _taxonomy(specialty)
    name = _named(head, "85")
    if name is None:
        return [*problems, f"{_at(head[0])}: the billing provider NM1*85 is missing"]
    tax = next((segment for segment in head if segment.id == "REF" and segment.get(1) == "EI"), None)
    tax_problems = [f"{_at(head[0])}: the billing provider REF*EI is missing"] if tax is None else []
    tax_problems += _pattern(tax, 2, EIN, "an EIN of nine digits") if tax is not None else []
    return problems + _provider(name) + _address(head, nine_digit=True) + tax_problems


def _subscriber(head: list[Segment]) -> list[str]:
    plan = _first(head, "SBR")
    if plan is None:
        return [f"{_at(head[0])}: SBR is missing"]
    is_self = head[0].get(4) == "0"
    problems = _expect(plan, {1: "P", 2: "18" if is_self else ""}) + _length(plan, 3, 0, 50)
    if plan.get(9) not in CLAIM_FILING_CODES:
        problems.append(f"{_at(plan)}: SBR09 is not a claim filing indicator")
    insured, payer = _named(head, "IL"), _named(head, "PR")
    if insured is None or payer is None:
        return [*problems, f"{_at(head[0])}: the subscriber or payer NM1 is missing"]
    problems += _person(insured) + _expect(insured, {8: "MI"}) + _length(insured, 9, 2, 80)
    problems += _organization(payer, "PR", "PI")
    return problems + (_address(head, nine_digit=False) + _demographics(head) if is_self else [])


def _patient(head: list[Segment]) -> list[str]:
    relation, name = _first(head, "PAT"), _named(head, "QC")
    if relation is None or name is None:
        return [f"{_at(head[0])}: PAT or the patient NM1*QC is missing"]
    problems = [] if relation.get(1) in PATIENT_RELATIONSHIPS else [f"{_at(relation)}: PAT01 is not allowed"]
    return problems + _person(name) + _address(head, nine_digit=False) + _demographics(head)


def _claim(claim: list[Segment]) -> list[str]:
    clm = claim[0]
    lines = _split(claim, "LX")
    head = claim[: len(claim) - sum(len(line) for line in lines)]
    problems = _length(clm, 1, 1, 20) + _expect(clm, {6: "Y", 7: "A", 8: "Y", 9: "Y"}) + _amount(clm, 2)
    place = clm.parts(5)
    if len(place) != 3 or PLACE.fullmatch(place[0]) is None or place[1] != "B" or place[2] not in FREQUENCIES:
        problems.append(f"{_at(clm)}: CLM05 must be place of service, B and a frequency code")
    diagnoses = _diagnoses(head)
    problems += diagnoses[1]
    rendering = _named(head, "82")
    problems += _provider(rendering) if rendering is not None else []
    if not 0 < len(lines) <= MAX_LINES:
        problems.append(f"{_at(clm)}: a claim needs 1 to {MAX_LINES} service lines")
    for number, line in enumerate(lines, start=1):
        problems += _line(line, number, diagnoses[0])
    charged = sum(_cents(line_sv1) for line in lines if (line_sv1 := _first(line, "SV1")) is not None)
    if not problems and charged != _cents(clm):
        problems.append(f"{_at(clm)}: CLM02 does not equal the sum of the service line charges")
    return problems


def _diagnoses(head: list[Segment]) -> tuple[int, list[str]]:
    codes = _first(head, "HI")
    if codes is None:
        return 0, [f"{_at(head[0])}: HI is missing"]
    pairs = [codes.parts(number) for number in range(1, len(codes.elements) + 1)]
    problems = [] if 0 < len(pairs) <= MAX_DIAGNOSES else [f"{_at(codes)}: HI must hold 1 to {MAX_DIAGNOSES} codes"]
    for index, pair in enumerate(pairs):
        qualifier = "ABK" if index == 0 else "ABF"
        if len(pair) != 2 or pair[0] != qualifier or "." in pair[1] or not is_icd_shaped(pair[1]):
            problems.append(f"{_at(codes)}: HI{index + 1:02d} must be {qualifier} and an ICD-10-CM code without a dot")
    return len(pairs), problems


def _line(line: list[Segment], number: int, diagnoses: int) -> list[str]:
    lx, service, dated = line[0], _first(line, "SV1"), _first(line, "DTP")
    problems = _expect(lx, {1: str(number)})
    if service is None or dated is None:
        return [*problems, f"{_at(lx)}: a service line needs SV1 and DTP*472"]
    procedure = service.parts(1)
    if len(procedure) < 2 or procedure[0] != "HC" or CPT_PATTERN.fullmatch(procedure[1]) is None:
        problems.append(f"{_at(service)}: SV101 must be HC and a CPT or HCPCS code")
    modifiers = procedure[2:]
    if len(modifiers) > MAX_MODIFIERS or any(MODIFIER_PATTERN.fullmatch(item) is None for item in modifiers):
        problems.append(f"{_at(service)}: SV101 holds at most {MAX_MODIFIERS} two-character modifiers")
    problems += _amount(service, 2) + _expect(service, {3: "UN"}) + _pattern(service, 4, DIGITS, "whole units")
    pointers = service.parts(7)
    valid = all(DIGITS.fullmatch(item) and 1 <= int(item) <= diagnoses for item in pointers)
    if not 0 < len(pointers) <= MAX_POINTERS or len(set(pointers)) != len(pointers) or not valid:
        problems.append(f"{_at(service)}: SV107 must point to 1 to {MAX_POINTERS} of the claim's diagnoses")
    return problems + _expect(dated, {1: "472", 2: "D8"}) + _date(dated, 3)


def _provider(name: Segment) -> list[str]:
    problems = _expect(name, {8: "XX"})
    problems += [] if is_valid_npi(name.get(9)) else [f"{_at(name)}: NM109 is not a valid NPI"]
    return problems + (_person(name) if name.get(2) == "1" else _length(name, 3, 1, 60))


def _organization(name: Segment, entity: str, qualifier: str) -> list[str]:
    return _expect(name, {1: entity, 2: "2", 8: qualifier}) + _length(name, 3, 1, 60) + _length(name, 9, 2, 80)


def _person(name: Segment) -> list[str]:
    return _expect(name, {2: "1"}) + _length(name, 3, 1, 60) + _length(name, 4, 1, 35)


def _address(head: list[Segment], *, nine_digit: bool) -> list[str]:
    street, place = _first(head, "N3"), _first(head, "N4")
    if street is None or place is None:
        return [f"{_at(head[0])}: N3 or N4 is missing"]
    problems = _length(street, 1, 1, 55) + _length(street, 2, 0, 55) + _length(place, 1, 1, 30)
    if place.get(2) not in LICENSE_STATES:
        problems.append(f"{_at(place)}: N402 is not a US state")
    return problems + _pattern(place, 3, ZIP_NINE if nine_digit else ZIP, "a five or nine-digit ZIP code")


def _demographics(head: list[Segment]) -> list[str]:
    facts = _first(head, "DMG")
    if facts is None:
        return [f"{_at(head[0])}: DMG is missing"]
    problems = _expect(facts, {1: "D8"}) + _date(facts, 2)
    return problems + ([] if facts.get(3) in SEXES else [f"{_at(facts)}: DMG03 must be F, M or U"])


def _taxonomy(segment: Segment) -> list[str]:
    return [] if is_taxonomy_code(segment.get(3)) else [f"{_at(segment)}: PRV03 is not a taxonomy code"]


def _expect(segment: Segment, values: Mapping[int, str]) -> list[str]:
    return [
        f"{_at(segment)}: {segment.id}{number:02d} must be {value or 'empty'}"
        for number, value in values.items()
        if segment.get(number) != value
    ]


def _length(segment: Segment, number: int, low: int, high: int) -> list[str]:
    size = len(segment.get(number))
    return [] if low <= size <= high else [f"{_at(segment)}: {segment.id}{number:02d} must be {low} to {high} long"]


def _pattern(segment: Segment, number: int, shape: re.Pattern[str], meaning: str) -> list[str]:
    return (
        [] if shape.fullmatch(segment.get(number)) else [f"{_at(segment)}: {segment.id}{number:02d} must be {meaning}"]
    )


def _amount(segment: Segment, number: int) -> list[str]:
    value = segment.get(number)
    if AMOUNT.fullmatch(value) is None or Decimal(value) <= 0:
        return [f"{_at(segment)}: {segment.id}{number:02d} must be a positive amount"]
    return []


def _date(segment: Segment, number: int) -> list[str]:
    try:
        datetime.strptime(segment.get(number), "%Y%m%d")
    except ValueError:
        return [f"{_at(segment)}: {segment.id}{number:02d} must be a date (CCYYMMDD)"]
    return []


def _cents(segment: Segment) -> int:
    value = segment.get(2)
    return int(Decimal(value) * 100) if AMOUNT.fullmatch(value) else -1


def _named(segments: Sequence[Segment], entity: str) -> Segment | None:
    return next((segment for segment in segments if segment.id == "NM1" and segment.get(1) == entity), None)


def _first(segments: Sequence[Segment], name: str) -> Segment | None:
    return next((segment for segment in segments if segment.id == name), None)


def _split(segments: Sequence[Segment], opener: str) -> list[list[Segment]]:
    blocks: list[list[Segment]] = []
    for segment in segments:
        if segment.id == opener:
            blocks.append([segment])
        elif blocks:
            blocks[-1].append(segment)
    return blocks


def _at(segment: Segment) -> str:
    return f"{segment.id} at segment {segment.position}"
