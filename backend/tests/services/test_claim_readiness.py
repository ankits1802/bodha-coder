from dataclasses import replace
from datetime import date
from typing import Any

import pytest

from app.codes.ncci import ncci_tables
from app.core.errors import Invalid
from app.models import ApprovedClaim, ClaimDetail, ClearinghouseConnection, Note, Provider
from app.services.billing_profile import billing_profile
from app.services.claim_837 import Address, BillingProvider, Payer, Person, Rendering, ServiceLine, Subscriber
from app.services.claim_assembly import claim_ref, professional_claim
from app.services.claim_inputs import ClaimContext, ClaimSource
from app.services.claim_readiness import missing_items

NOTE_ID = "1a2b3c4d-5e6f-7a8b-9c0d-000000000001"
SERVICE_DAY = date(2026, 11, 25)
PRACTICE = {
    "legal_name": "Lakeside Family Medicine",
    "tax_id": "12-3456789",
    "group_npi": "1245319599",
    "taxonomy_code": "207Q00000X",
    "address": "123 Main St",
    "city": "Springfield",
    "state": "IL",
    "zip": "62701-1234",
    "phone": "555-555-1234",
    "billing_contact": "Dana Biller",
}
PROFILE = billing_profile({"practice_details": PRACTICE})
GROUP_DETAILS = {"taxonomy_code": "207R00000X", "bills_under": "group", "group_npi": "1245319599"}
MEDICARE = {"id": "payer-1", "name": "Medicare Part B", "payer_id": "MCRB", "plan_type": "medicare", "active": True}
CODES = [
    {"code": "99214", "type": "CPT", "modifiers": ["25"], "units": 1},
    {"code": "96127", "type": "CPT", "modifiers": [], "units": 2, "pointers": ["R20.2"]},
    {"code": "E11.65", "type": "ICD-10", "modifiers": [], "units": 1},
    {"code": "I10", "type": "ICD-10", "modifiers": [], "units": 1},
    {"code": "R20.2", "type": "ICD-10", "modifiers": [], "units": 1},
]
PRACTICE_ADDRESS = Address("123 Main St", None, "Springfield", "IL", "627011234")


def _detail(**changes: Any) -> ClaimDetail:
    values = {
        "id": "detail-1",
        "patient_last": "Reyes",
        "patient_first": "Marisol",
        "patient_birth_date": date(1959, 3, 12),
        "patient_sex": "F",
        "street": "9 Elm St",
        "street_2": None,
        "city": "Springfield",
        "state": "IL",
        "zip_code": "62704",
        "relationship": "18",
        "member_id": "1EG4TE5MK72",
        "group_number": None,
        "subscriber_last": None,
        "subscriber_first": None,
    }
    return ClaimDetail(**{**values, **changes})


def _context(**changes: Any) -> ClaimContext:
    base = ClaimContext(
        profile=PROFILE,
        connection=ClearinghouseConnection(name="Office Ally"),
        charges={"99214": 15000, "96127": 1000},
        payers={"payer-1": MEDICARE},
        tables=ncci_tables(),
    )
    return replace(base, **changes)


def _source(*, details: dict | None = None, name: str = "Elena Varga", **changes: Any) -> ClaimSource:
    note = Note(id=NOTE_ID, payer="payer-1", service_date=SERVICE_DAY, place_code="11", patient_name="Reyes Marisol")
    provider = Provider(name=name, npi="1234567893", details=GROUP_DETAILS if details is None else details)
    snapshot = ApprovedClaim(id="snapshot-1", revision=1, content={"codes": CODES})
    return replace(ClaimSource(note, provider, snapshot, _detail()), **changes)


def test_a_complete_claim_is_ready_and_carries_charge_times_units_and_numbered_pointers():
    claim = professional_claim(_context(), _source())

    assert missing_items(_context(), _source()) == ()
    assert (claim.claim_ref, claim.place_code, claim.diagnoses) == (
        "1A2B3C4D-5E6F-7A8B-9",
        "11",
        ("E1165", "I10", "R202"),
    )
    assert claim.lines == (
        ServiceLine("99214", ("25",), 15000, 1, (1, 2, 3), SERVICE_DAY),
        ServiceLine("96127", (), 2000, 2, (3,), SERVICE_DAY),
    )
    assert claim.billing == BillingProvider(
        "Lakeside Family Medicine", None, "1245319599", "123456789", "207Q00000X", PRACTICE_ADDRESS
    )
    assert claim.rendering == Rendering(Person("Varga", "Elena"), "1234567893", "207R00000X")
    assert claim.payer == Payer("Medicare Part B", "MCRB", "MB")
    assert claim.subscriber == Subscriber(Person("Reyes", "Marisol"), "1EG4TE5MK72", None, "18")
    assert claim.charge_cents == 17000


def test_an_empty_practice_lists_everything_a_claim_still_needs():
    empty = _context(profile=billing_profile({}), connection=None, charges={}, payers={})

    assert missing_items(empty, _source(detail=None)) == (
        "connection",
        "practice.legal_name",
        "practice.tax_id",
        "practice.address",
        "practice.city",
        "practice.state",
        "practice.zip",
        "practice.phone",
        "practice.billing_contact",
        "payer",
        "details",
        "charge:99214",
        "charge:96127",
    )


def test_the_billing_npi_comes_from_the_provider_group_then_the_practice():
    no_group = {"taxonomy_code": "207R00000X"}
    assert missing_items(_context(), _source(details=no_group)) == ()
    assert professional_claim(_context(), _source(details=no_group)).billing.npi == "1245319599"
    bare = _context(profile=replace(PROFILE, group_npi=None))
    assert missing_items(bare, _source(details=no_group)) == ("practice.npi",)


def test_an_individual_biller_is_the_billing_provider_and_sends_no_rendering_provider():
    claim = professional_claim(
        _context(), _source(details={"bills_under": "individual", "taxonomy_code": "207R00000X"})
    )

    assert claim.billing == BillingProvider(
        "Elena Varga", Person("Varga", "Elena"), "1234567893", "123456789", "207R00000X", PRACTICE_ADDRESS
    )
    assert claim.rendering is None


def test_payer_ids_filing_codes_charges_and_provider_names_are_named_when_missing():
    other = {**MEDICARE, "payer_id": None, "plan_type": "other"}
    assert missing_items(_context(payers={"payer-1": other}), _source()) == ("payer.id", "payer.filing")
    chosen = {**other, "payer_id": "60054", "claim_filing": "CI"}
    assert missing_items(_context(payers={"payer-1": chosen}), _source()) == ()
    assert missing_items(_context(charges={"99214": 15000}), _source()) == ("charge:96127",)
    assert missing_items(_context(), _source(name="Varga")) == ("provider.name",)


def test_a_claim_that_cannot_be_built_from_its_snapshot_is_flagged():
    procedures_only = ApprovedClaim(id="snapshot-2", revision=2, content={"codes": CODES[:2]})
    assert missing_items(_context(), _source(snapshot=procedures_only)) == ("codes",)
    assert missing_items(_context(), _source(snapshot=None)) == ("codes",)


def test_assembly_refuses_a_claim_that_is_not_ready():
    with pytest.raises(Invalid, match="details"):
        professional_claim(_context(), _source(detail=None))


def test_a_dependent_claim_names_the_subscriber():
    spouse = _detail(relationship="01", subscriber_last="Reyes", subscriber_first="Jose", group_number="GRP9")

    claim = professional_claim(_context(), _source(detail=spouse))

    assert claim.subscriber == Subscriber(Person("Reyes", "Jose"), "1EG4TE5MK72", "GRP9", "01")
    assert claim.patient.person == Person("Reyes", "Marisol")


def test_the_claim_reference_is_the_note_id_prefix_in_upper_case():
    assert claim_ref(NOTE_ID) == "1A2B3C4D-5E6F-7A8B-9"
