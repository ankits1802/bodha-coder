from __future__ import annotations

import asyncio
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.codes.ncci import NcciTables, ncci_tables
from app.codes.npi import is_valid_npi
from app.codes.x12_codes import default_filing_code
from app.models import ApprovedClaim, ClaimDetail, ClearinghouseConnection, Note, Practice, Provider
from app.services.billing_profile import BillingProfile, billing_profile
from app.services.charge_schedule import charge_schedule
from app.services.claim_837 import Person
from app.services.claim_details import latest_details
from app.services.claim_lines import INDIVIDUAL, Claim, add_on_primaries, billing_npi, build_claim, claim_party
from app.services.claim_snapshots import latest_snapshots, snapshot_codes
from app.services.clearinghouse_settings import current_connection
from app.services.payers import payer_list

__all__ = [
    "BillingParty",
    "ClaimContext",
    "ClaimSource",
    "billing_party",
    "claim_context",
    "claim_of",
    "claim_sources",
    "filing_code",
    "payer_of",
    "person_named",
]


@dataclass(frozen=True)
class ClaimContext:
    profile: BillingProfile
    connection: ClearinghouseConnection | None
    charges: Mapping[str, int]
    payers: Mapping[str, Mapping[str, Any]]
    tables: NcciTables


@dataclass(frozen=True)
class ClaimSource:
    note: Note
    provider: Provider
    snapshot: ApprovedClaim | None
    detail: ClaimDetail | None


@dataclass(frozen=True)
class BillingParty:
    npi: str | None
    individual: bool
    taxonomy: str | None


async def claim_context(db: AsyncSession, practice: Practice) -> ClaimContext:
    return ClaimContext(
        profile=billing_profile(practice.setup),
        connection=await current_connection(db, practice.id),
        charges=charge_schedule(practice),
        payers={payer["id"]: payer for payer in payer_list(practice) if payer.get("active")},
        tables=await asyncio.to_thread(ncci_tables),
    )


async def claim_sources(db: AsyncSession, rows: Sequence[tuple[Note, Provider]]) -> list[ClaimSource]:
    note_ids = [note.id for note, _ in rows]
    snapshots, details = await latest_snapshots(db, note_ids), await latest_details(db, note_ids)
    return [ClaimSource(note, provider, snapshots.get(note.id), details.get(note.id)) for note, provider in rows]


def claim_of(context: ClaimContext, source: ClaimSource) -> Claim | None:
    if source.snapshot is None:
        return None
    codes = snapshot_codes(source.snapshot)
    primaries = add_on_primaries(context.tables, codes, source.note.service_date)
    return build_claim(claim_party(source.note, source.provider), codes, primaries=primaries)


def billing_party(context: ClaimContext, provider: Provider) -> BillingParty:
    details = provider.details or {}
    if details.get("bills_under") == INDIVIDUAL:
        return BillingParty(_valid_npi(provider.npi), True, details.get("taxonomy_code") or None)
    group = billing_npi(provider.npi, details) or context.profile.group_npi
    return BillingParty(_valid_npi(group), False, context.profile.taxonomy)


def payer_of(context: ClaimContext, note: Note) -> Mapping[str, Any] | None:
    return context.payers.get(note.payer) if note.payer else None


def filing_code(payer: Mapping[str, Any]) -> str | None:
    return payer.get("claim_filing") or default_filing_code(payer.get("plan_type"))


def person_named(name: str) -> Person | None:
    words = name.split()
    return Person(words[-1], " ".join(words[:-1])) if len(words) > 1 else None


def _valid_npi(npi: str | None) -> str | None:
    return npi if npi and is_valid_npi(npi) else None
