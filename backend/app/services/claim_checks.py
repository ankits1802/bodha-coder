from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.codes.billing_codes import Code
from app.codes.ncci import NcciTables, ncci_tables
from app.codes.payer_rules import PayerClaim, payer_flags, payer_for
from app.core.deps import Actor
from app.models import Note, Provider
from app.services.audit_log import record_access
from app.services.payers import payer_list
from app.services.review_actions import current_claim, note_for

__all__ = ["PHYSICIAN_CREDENTIALS", "claim_checks", "edits_for"]

PHYSICIAN_CREDENTIALS = frozenset({"MD", "DO"})


async def claim_checks(db: AsyncSession, actor: Actor, note_id: str) -> dict[str, Any]:
    note = await note_for(db, actor, note_id)
    provider = await db.get_one(Provider, note.provider_id)
    codes = await current_claim(db, note)
    tables = await asyncio.to_thread(ncci_tables)
    payer = _note_payer(actor, note)
    facts = PayerClaim(codes, note.patient_age, _supervised_nonphysician(provider))
    payer_kind = payer_for(payer.get("plan_type"), payer.get("name")) if payer else None
    flags = payer_flags(facts, payer_kind, note.place_code, note.service_date) if payer_kind else []
    record_access(db, actor, "checked claim edits", note_id=note.id)
    await db.commit()
    return {
        "ncci": {"quarter": tables.quarter, "covers": tables.covers(note.service_date)},
        "edits": edits_for(tables, codes, note),
        "payer": {"name": payer["name"], "plan_type": payer.get("plan_type")} if payer else None,
        "payer_flags": [flag.as_json() for flag in flags],
    }


def edits_for(tables: NcciTables, codes: tuple[Code, ...], note: Note) -> list[dict[str, object]]:
    if not tables.covers(note.service_date):
        return []
    return [edit.as_json() for edit in tables.claim_edits(codes, note.service_date)]


def _note_payer(actor: Actor, note: Note) -> Mapping[str, Any] | None:
    if note.payer is None or actor.practice is None:
        return None
    return next((payer for payer in payer_list(actor.practice) if payer.get("id") == note.payer), None)


def _supervised_nonphysician(provider: Provider) -> bool:
    details = provider.details or {}
    return provider.credential not in PHYSICIAN_CREDENTIALS and bool(details.get("supervising_physician"))
