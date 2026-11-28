from __future__ import annotations

from app.core.errors import Invalid
from app.models import CLAIM_REF_LENGTH, SELF_RELATIONSHIP, ClaimDetail
from app.services.claim_837 import (
    Address,
    BillingProvider,
    Patient,
    Payer,
    Person,
    ProfessionalClaim,
    Rendering,
    ServiceLine,
    Subscriber,
)
from app.services.claim_inputs import ClaimContext, ClaimSource, billing_party, claim_of, filing_code, payer_of
from app.services.claim_inputs import person_named as _person
from app.services.claim_lines import POINTER_LETTERS, Claim
from app.services.claim_readiness import missing_items

__all__ = ["claim_ref", "professional_claim"]


def claim_ref(note_id: str) -> str:
    return note_id[:CLAIM_REF_LENGTH].upper()


def professional_claim(context: ClaimContext, source: ClaimSource) -> ProfessionalClaim:
    missing = missing_items(context, source)
    claim = claim_of(context, source)
    payer = payer_of(context, source.note)
    detail = source.detail
    if missing or claim is None or payer is None or detail is None:
        raise Invalid(f"note {source.note.id} is missing {', '.join(missing) or 'claim information'}")
    patient = Patient(
        Person(detail.patient_last, detail.patient_first),
        detail.patient_birth_date,
        detail.patient_sex,
        _patient_address(detail),
    )
    return ProfessionalClaim(
        claim_ref=claim_ref(source.note.id),
        place_code=source.note.place_code,
        diagnoses=claim.diagnoses,
        billing=_billing_provider(context, source),
        rendering=_rendering(context, source),
        subscriber=_subscriber(detail, patient.person),
        patient=patient,
        payer=Payer(str(payer["name"]), str(payer["payer_id"]), str(filing_code(payer))),
        lines=_lines(context, source, claim),
    )


def _billing_provider(context: ClaimContext, source: ClaimSource) -> BillingProvider:
    profile, party = context.profile, billing_party(context, source.provider)
    address = Address(
        str(profile.street), profile.street_2, str(profile.city), str(profile.state), str(profile.zip_code)
    )
    person = _person(source.provider.name) if party.individual else None
    name = source.provider.name if party.individual else str(profile.legal_name)
    return BillingProvider(name, person, str(party.npi), str(profile.tax_id), party.taxonomy, address)


def _rendering(context: ClaimContext, source: ClaimSource) -> Rendering | None:
    provider, party = source.provider, billing_party(context, source.provider)
    person = _person(provider.name)
    if party.individual or person is None or provider.npi is None:
        return None
    return Rendering(person, provider.npi, (provider.details or {}).get("taxonomy_code") or None)


def _subscriber(detail: ClaimDetail, patient: Person) -> Subscriber:
    is_self = detail.relationship == SELF_RELATIONSHIP
    person = patient if is_self else Person(str(detail.subscriber_last), str(detail.subscriber_first))
    return Subscriber(person, detail.member_id, detail.group_number, detail.relationship)


def _patient_address(detail: ClaimDetail) -> Address:
    return Address(detail.street, detail.street_2, detail.city, detail.state, detail.zip_code)


def _lines(context: ClaimContext, source: ClaimSource, claim: Claim) -> tuple[ServiceLine, ...]:
    return tuple(
        ServiceLine(
            code=line.code,
            modifiers=line.modifiers,
            charge_cents=context.charges[line.code] * line.units,
            units=line.units,
            pointers=tuple(POINTER_LETTERS.index(letter) + 1 for letter in line.pointers),
            service_date=source.note.service_date,
        )
        for line in claim.lines
    )
