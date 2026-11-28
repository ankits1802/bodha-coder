from __future__ import annotations

from app.codes.npi import is_valid_npi
from app.core.errors import Invalid
from app.services.billing_profile import missing_from_profile
from app.services.claim_inputs import ClaimContext, ClaimSource, billing_party, claim_of, filing_code, payer_of
from app.services.claim_inputs import person_named as _person

__all__ = ["CHARGE_PREFIX", "missing_items"]

CHARGE_PREFIX = "charge:"


def missing_items(context: ClaimContext, source: ClaimSource) -> tuple[str, ...]:
    found = [] if context.connection else ["connection"]
    found += missing_from_profile(context.profile)
    found += _provider_items(context, source)
    found += _payer_items(context, source)
    if source.detail is None:
        found.append("details")
    found += _code_items(context, source)
    return tuple(dict.fromkeys(found))


def _provider_items(context: ClaimContext, source: ClaimSource) -> list[str]:
    provider, party = source.provider, billing_party(context, source.provider)
    found: list[str] = []
    if not (provider.npi and is_valid_npi(provider.npi)):
        found.append("provider.npi")
    if party.npi is None and not party.individual:
        found.append("practice.npi")
    if _person(provider.name) is None:
        found.append("provider.name")
    return found


def _payer_items(context: ClaimContext, source: ClaimSource) -> list[str]:
    payer = payer_of(context, source.note)
    if payer is None:
        return ["payer"]
    found = [] if payer.get("payer_id") else ["payer.id"]
    return found + ([] if filing_code(payer) else ["payer.filing"])


def _code_items(context: ClaimContext, source: ClaimSource) -> list[str]:
    try:
        claim = claim_of(context, source)
    except Invalid:
        return ["codes"]
    if claim is None:
        return ["codes"]
    return [f"{CHARGE_PREFIX}{line.code}" for line in claim.lines if line.code not in context.charges]
