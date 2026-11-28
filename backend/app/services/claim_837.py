from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from itertools import count

from app.services.x12_writer import Interchange, amount, composite, segment, text, write_interchange

__all__ = [
    "FREQUENCY_ORIGINAL",
    "IMPLEMENTATION",
    "MAX_LINES",
    "SELF",
    "Address",
    "BillingProvider",
    "ClaimFile",
    "Patient",
    "Payer",
    "Person",
    "ProfessionalClaim",
    "Receiver",
    "Rendering",
    "ServiceLine",
    "Submitter",
    "Subscriber",
    "write_837p",
]

IMPLEMENTATION = "005010X222A1"
FREQUENCY_ORIGINAL = "1"
SELF = "18"
MAX_LINES = 50
ORGANIZATION, INDIVIDUAL = "2", "1"
PRINCIPAL, OTHER_DIAGNOSIS = "ABK", "ABF"
NAME_LIMIT, FIRST_LIMIT, STREET_LIMIT, CITY_LIMIT, REFERENCE_LIMIT = 60, 35, 55, 30, 50
DATE_FORMAT = "%Y%m%d"


@dataclass(frozen=True)
class Address:
    street: str
    street_2: str | None
    city: str
    state: str
    zip_code: str


@dataclass(frozen=True)
class Person:
    last: str
    first: str


@dataclass(frozen=True)
class BillingProvider:
    name: str
    person: Person | None
    npi: str
    tax_id: str
    taxonomy: str | None
    address: Address


@dataclass(frozen=True)
class Rendering:
    person: Person
    npi: str
    taxonomy: str | None


@dataclass(frozen=True)
class Patient:
    person: Person
    birth_date: date
    sex: str
    address: Address


@dataclass(frozen=True)
class Subscriber:
    person: Person
    member_id: str
    group_number: str | None
    relationship: str


@dataclass(frozen=True)
class Payer:
    name: str
    payer_id: str
    filing_code: str


@dataclass(frozen=True)
class ServiceLine:
    code: str
    modifiers: tuple[str, ...]
    charge_cents: int
    units: int
    pointers: tuple[int, ...]
    service_date: date


@dataclass(frozen=True)
class ProfessionalClaim:
    claim_ref: str
    place_code: str
    diagnoses: tuple[str, ...]
    billing: BillingProvider
    rendering: Rendering | None
    subscriber: Subscriber
    patient: Patient
    payer: Payer
    lines: tuple[ServiceLine, ...]
    frequency: str = FREQUENCY_ORIGINAL

    @property
    def charge_cents(self) -> int:
        return sum(line.charge_cents for line in self.lines)


@dataclass(frozen=True)
class Submitter:
    name: str
    contact: str
    phone: str


@dataclass(frozen=True)
class Receiver:
    name: str


@dataclass(frozen=True)
class ClaimFile:
    interchange: Interchange
    batch_ref: str
    submitter: Submitter
    receiver: Receiver
    claims: tuple[ProfessionalClaim, ...]


def write_837p(claim_file: ClaimFile) -> str:
    if not claim_file.claims:
        raise ValueError("a claim file needs at least one claim")
    too_long = [claim.claim_ref for claim in claim_file.claims if not 0 < len(claim.lines) <= MAX_LINES]
    if too_long:
        raise ValueError(f"claims {', '.join(too_long)} need 1 to {MAX_LINES} service lines")
    return write_interchange(claim_file.interchange, [*_header(claim_file), *_hierarchy(claim_file.claims)])


def _header(claim_file: ClaimFile) -> list[str]:
    made, interchange = claim_file.interchange.created, claim_file.interchange
    submitter = claim_file.submitter
    return [
        segment("BHT", "0019", "00", claim_file.batch_ref, made.strftime(DATE_FORMAT), made.strftime("%H%M"), "CH"),
        _organization("41", submitter.name, "46", interchange.sender_id),
        segment("PER", "IC", text(submitter.contact, NAME_LIMIT), "TE", submitter.phone),
        _organization("40", claim_file.receiver.name, "46", interchange.receiver_id),
    ]


def _hierarchy(claims: tuple[ProfessionalClaim, ...]) -> list[str]:
    grouped: dict[BillingProvider, list[ProfessionalClaim]] = {}
    for claim in claims:
        grouped.setdefault(claim.billing, []).append(claim)
    numbers = count(1)
    found: list[str] = []
    for billing, group in grouped.items():
        parent = next(numbers)
        found += _billing_loop(parent, billing)
        for claim in group:
            found += _subscriber_loop(claim, parent, numbers)
    return found


def _billing_loop(number: int, billing: BillingProvider) -> list[str]:
    found = [segment("HL", str(number), "", "20", "1")]
    if billing.taxonomy:
        found.append(segment("PRV", "BI", "PXC", billing.taxonomy))
    name = (
        _individual("85", billing.person, "XX", billing.npi)
        if billing.person
        else _organization("85", billing.name, "XX", billing.npi)
    )
    return [*found, name, *_address(billing.address), segment("REF", "EI", billing.tax_id)]


def _subscriber_loop(claim: ProfessionalClaim, parent: int, numbers: count) -> list[str]:
    subscriber, payer = claim.subscriber, claim.payer
    number, is_self = next(numbers), subscriber.relationship == SELF
    found = [
        segment("HL", str(number), str(parent), "22", "0" if is_self else "1"),
        segment(
            "SBR",
            "P",
            SELF if is_self else "",
            text(subscriber.group_number or "", REFERENCE_LIMIT),
            *([""] * 5),
            payer.filing_code,
        ),
        _individual("IL", subscriber.person, "MI", subscriber.member_id),
    ]
    if is_self:
        found += [*_address(claim.patient.address), _demographics(claim.patient)]
    found.append(_organization("PR", payer.name, "PI", payer.payer_id))
    if not is_self:
        found += _patient_loop(claim, next(numbers), number)
    return [*found, *_claim_loop(claim)]


def _patient_loop(claim: ProfessionalClaim, number: int, parent: int) -> list[str]:
    patient = claim.patient
    return [
        segment("HL", str(number), str(parent), "23", "0"),
        segment("PAT", claim.subscriber.relationship),
        _individual("QC", patient.person, "", ""),
        *_address(patient.address),
        _demographics(patient),
    ]


def _claim_loop(claim: ProfessionalClaim) -> list[str]:
    found = [
        segment(
            "CLM",
            claim.claim_ref,
            amount(claim.charge_cents),
            "",
            "",
            composite(claim.place_code, "B", claim.frequency),
            "Y",
            "A",
            "Y",
            "Y",
        ),
        segment(
            "HI",
            *(
                composite(PRINCIPAL if index == 0 else OTHER_DIAGNOSIS, code)
                for index, code in enumerate(claim.diagnoses)
            ),
        ),
    ]
    if claim.rendering is not None:
        found.append(_individual("82", claim.rendering.person, "XX", claim.rendering.npi))
        if claim.rendering.taxonomy:
            found.append(segment("PRV", "PE", "PXC", claim.rendering.taxonomy))
    for number, line in enumerate(claim.lines, start=1):
        found += _service_line(number, line)
    return found


def _service_line(number: int, line: ServiceLine) -> list[str]:
    return [
        segment("LX", str(number)),
        segment(
            "SV1",
            composite("HC", line.code, *line.modifiers),
            amount(line.charge_cents),
            "UN",
            str(line.units),
            "",
            "",
            composite(*(str(pointer) for pointer in line.pointers)),
        ),
        segment("DTP", "472", "D8", line.service_date.strftime(DATE_FORMAT)),
    ]


def _organization(entity: str, name: str, qualifier: str, identifier: str) -> str:
    return segment("NM1", entity, ORGANIZATION, text(name, NAME_LIMIT), "", "", "", "", qualifier, identifier)


def _individual(entity: str, person: Person, qualifier: str, identifier: str) -> str:
    last, first = text(person.last, NAME_LIMIT), text(person.first, FIRST_LIMIT)
    return segment("NM1", entity, INDIVIDUAL, last, first, "", "", "", qualifier, identifier)


def _address(address: Address) -> list[str]:
    street_2 = text(address.street_2, STREET_LIMIT) if address.street_2 else ""
    return [
        segment("N3", text(address.street, STREET_LIMIT), street_2),
        segment("N4", text(address.city, CITY_LIMIT), address.state, address.zip_code),
    ]


def _demographics(patient: Patient) -> str:
    return segment("DMG", "D8", patient.birth_date.strftime(DATE_FORMAT), patient.sex)
