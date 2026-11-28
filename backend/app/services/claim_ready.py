from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Actor
from app.core.errors import Conflict, Invalid
from app.models import Note, Practice, Provider, utcnow
from app.services.claim_exports import HELD, approved_unexported
from app.services.claim_holds import held_for_confirmation
from app.services.claim_inputs import ClaimContext, ClaimSource, claim_context, claim_sources
from app.services.claim_readiness import missing_items
from app.services.claim_status import SENDING, ClaimState, claim_states
from app.services.clearinghouse_settings import current_connection

__all__ = ["ReadyClaims", "claim_columns", "clearinghouse_summary", "ready_claims"]

MISSING, READY = "missing", "ready"
NOT_READY = "some of the chosen claims are missing information or are already with the clearinghouse"


@dataclass(frozen=True)
class ReadyClaims:
    context: ClaimContext
    sources: list[ClaimSource]


async def ready_claims(db: AsyncSession, actor: Actor, note_ids: list[str] | None) -> ReadyClaims:
    query = approved_unexported(actor.practice_id).with_for_update(of=Note)
    if note_ids is not None:
        query = query.where(Note.id.in_(note_ids))
    rows = list((await db.execute(query)).tuples().all())
    found = [note.id for note, _ in rows]
    held = await held_for_confirmation(db, found)
    if note_ids is not None and held:
        raise Conflict(HELD)
    states = await claim_states(db, found, utcnow())
    open_rows = [(note, provider) for note, provider in rows if note.id not in held and _open(states.get(note.id))]
    context = await claim_context(db, actor.own_practice)
    sources = [source for source in await claim_sources(db, open_rows) if not missing_items(context, source)]
    if note_ids is not None and len(sources) != len(set(note_ids)):
        raise Invalid(NOT_READY)
    if not sources:
        raise Invalid("no claims are ready to send")
    return ReadyClaims(context, sources)


async def claim_columns(db: AsyncSession, practice: Practice, note_ids: Sequence[str]) -> dict[str, dict[str, Any]]:
    if not note_ids:
        return {}
    query = (
        select(Note, Provider)
        .join(Provider, Provider.id == Note.provider_id)
        .where(Note.practice_id == practice.id, Note.id.in_(note_ids))
    )
    rows = list((await db.execute(query)).tuples().all())
    context = await claim_context(db, practice)
    states = await claim_states(db, list(note_ids), utcnow())
    columns = {
        source.note.id: _column(context, source, states.get(source.note.id)) for source in await claim_sources(db, rows)
    }
    return {note_id: column for note_id, column in columns.items() if column is not None}


async def clearinghouse_summary(db: AsyncSession, practice_id: str) -> dict[str, str] | None:
    connection = await current_connection(db, practice_id)
    if connection is None:
        return None
    return {"name": connection.name, "transport": connection.transport, "usage": connection.usage}


def _open(state: ClaimState | None) -> bool:
    return state is None or state.resendable


def _column(context: ClaimContext, source: ClaimSource, state: ClaimState | None) -> dict[str, Any] | None:
    if source.note.exported_at is not None:
        return {**state.as_json(), "missing": []} if state is not None and not state.resendable else None
    if state is not None and state.status == SENDING:
        return {**state.as_json(), "missing": []}
    missing = list(missing_items(context, source))
    if state is not None:
        return {**state.as_json(), "missing": missing}
    return {"status": MISSING if missing else READY, "at": None, "reasons": [], "missing": missing}
