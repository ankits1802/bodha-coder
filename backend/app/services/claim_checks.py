from __future__ import annotations

import asyncio
from collections.abc import Mapping
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.codes.billing_codes import Code
from app.codes.ncci import NcciTables, ncci_tables
from app.codes.payer_rules import (
    EarlierVisit,
    PayerClaim,
    PayerFlag,
    initial_nursing_visits,
    payer_flags,
    payer_for,
    repeated_initial_visit,
)
from app.core.deps import Actor
from app.models import VOIDED, Note, Provider
from app.services.audit_log import record_access
from app.services.payers import payer_list
from app.services.remittance_matching import same_person
from app.services.review_actions import current_claim, note_for
from app.services.visit_levels import visit_codes

__all__ = ["PHYSICIAN_CREDENTIALS", "claim_checks", "edits_for", "stay_history"]

PHYSICIAN_CREDENTIALS = frozenset({"MD", "DO"})
HISTORY_COLUMNS = (Note.id, Note.patient_name, Note.patient_birth_date, Note.service_date, Note.place_code)


async def claim_checks(db: AsyncSession, actor: Actor, note_id: str) -> dict[str, Any]:
    note = await note_for(db, actor, note_id)
    provider = await db.get_one(Provider, note.provider_id)
    codes = await current_claim(db, note)
    tables = await asyncio.to_thread(ncci_tables)
    payer = _note_payer(actor, note)
    facts = PayerClaim(codes, note.patient_age, _supervised_nonphysician(provider))
    payer_kind = payer_for(payer.get("plan_type"), payer.get("name")) if payer else None
    flags = payer_flags(facts, payer_kind, note.place_code, note.service_date) if payer_kind else []
    repeated = await _repeated_initial_visit(db, note, provider, codes)
    flags += [repeated] if repeated else []
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


async def stay_history(db: AsyncSession, note: Note) -> list[EarlierVisit]:
    if not note.patient_name:
        return []
    rows = await db.execute(
        select(*HISTORY_COLUMNS, Provider.specialty)
        .join(Provider, Provider.id == Note.provider_id)
        .where(
            Note.practice_id == note.practice_id,
            Note.id != note.id,
            Note.status != VOIDED,
            Note.patient_name.is_not(None),
            Note.service_date <= note.service_date,
        )
    )
    same = [row for row in rows.all() if _same_patient(note, row.patient_name, row.patient_birth_date)]
    codes = await visit_codes(db, [row.id for row in same])
    return [
        EarlierVisit(row.service_date, row.place_code, codes[row.id], row.specialty) for row in same if row.id in codes
    ]


async def _repeated_initial_visit(
    db: AsyncSession, note: Note, provider: Provider, codes: tuple[Code, ...]
) -> PayerFlag | None:
    if not initial_nursing_visits(codes, note.place_code):
        return None
    history = await stay_history(db, note)
    return repeated_initial_visit(codes, note.place_code, note.service_date, history, specialty=provider.specialty)


def _same_patient(note: Note, name: str, birth_date: date | None) -> bool:
    if note.patient_birth_date and birth_date and note.patient_birth_date != birth_date:
        return False
    return same_person(note.patient_name or "", name)


def _note_payer(actor: Actor, note: Note) -> Mapping[str, Any] | None:
    if note.payer is None or actor.practice is None:
        return None
    return next((payer for payer in payer_list(actor.practice) if payer.get("id") == note.payer), None)


def _supervised_nonphysician(provider: Provider) -> bool:
    details = provider.details or {}
    return provider.credential not in PHYSICIAN_CREDENTIALS and bool(details.get("supervising_physician"))
