from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime

from app.services.claim_837 import (
    IMPLEMENTATION,
    Address,
    BillingProvider,
    ClaimFile,
    Patient,
    Payer,
    Person,
    ProfessionalClaim,
    Receiver,
    Rendering,
    ServiceLine,
    Submitter,
    Subscriber,
)
from app.services.x12_writer import Interchange

PRACTICE_ADDRESS = Address("123 Main St", "Suite 200", "Springfield", "IL", "627011234")
GROUP = BillingProvider("Lakeside Family Medicine", None, "1245319599", "123456789", "207Q00000X", PRACTICE_ADDRESS)
VARGA = Person("Varga", "Elena")
RENDERING = Rendering(VARGA, "1234567893", "207R00000X")
MARISOL = Person("Reyes", "Marisol")
HOME = Address("9 Elm St", None, "Springfield", "IL", "62704")
PATIENT = Patient(MARISOL, date(1959, 3, 12), "F", HOME)
MEDICARE = Payer("Medicare Part B", "MCRB", "MB")
SERVICE_DAY = date(2026, 11, 25)
OFFICE_VISIT = ServiceLine("99214", ("25",), 15000, 1, (1, 2), SERVICE_DAY)
SCREENING = ServiceLine("96127", (), 2500, 2, (1,), SERVICE_DAY)
CLAIM_REF = "1A2B3C4D-5E6F-7A8B-9"
MADE = datetime(2026, 11, 28, 14, 30)


def self_claim(**changes: object) -> ProfessionalClaim:
    claim = ProfessionalClaim(
        claim_ref=CLAIM_REF,
        place_code="11",
        diagnoses=("E1165", "I10"),
        billing=GROUP,
        rendering=RENDERING,
        subscriber=Subscriber(MARISOL, "1EG4TE5MK72", None, "18"),
        patient=PATIENT,
        payer=MEDICARE,
        lines=(OFFICE_VISIT, SCREENING),
    )
    return replace(claim, **changes)


def claim_file(*claims: ProfessionalClaim, control: int = 7, usage: str = "T") -> ClaimFile:
    return ClaimFile(
        interchange=Interchange("ZZ", "SUB123", "ZZ", "OFFALLY", usage, control, MADE, "HC", "837", IMPLEMENTATION),
        batch_ref="F00DBABE",
        submitter=Submitter("Lakeside Family Medicine", "Dana Biller", "5555551234"),
        receiver=Receiver("Office Ally"),
        claims=claims,
    )
