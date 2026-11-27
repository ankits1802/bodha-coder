from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.object_store import ObjectStore
from app.codes.billing_codes import Code
from app.codes.em import is_em_code
from app.codes.icd import IcdCatalog, IcdRelease
from app.codes.modifiers import PROCEDURE_MODIFIERS, VISIT_MODIFIERS
from app.core.deps import Actor
from app.core.errors import Conflict, Invalid, NotFound
from app.models import AuditSample, Note, utcnow
from app.services.agreement import ClaimElements, compare_elements, elements_of
from app.services.audit_log import record_access
from app.services.audit_samples import sample_rows
from app.services.note_texts import current_texts, note_texts
from app.services.note_view import pdf_link

__all__ = ["KNOWN_MODIFIERS", "check_answer", "item_document", "next_item", "reviewer_item", "submit_answer"]

KNOWN_MODIFIERS = frozenset(VISIT_MODIFIERS) | frozenset(PROCEDURE_MODIFIERS)


async def next_item(db: AsyncSession, actor: Actor, sample_id: str) -> dict[str, Any]:
    mine = [item for item in await sample_rows(db, actor.practice_id, sample_id) if item.reviewer_id == actor.user.id]
    if not mine:
        raise NotFound("sample not found")
    waiting = [item for item in mine if item.status == "open"]
    progress = {"id": sample_id, "purpose": mine[0].purpose, "total": len(mine), "done": len(mine) - len(waiting)}
    if not waiting:
        return {"sample": progress, "item": None}
    item = waiting[0]
    texts = current_texts(await note_texts(db, item.note_id))
    record_access(db, actor, "opened note for blind review", note_id=item.note_id)
    await db.commit()
    return {
        "sample": progress,
        "item": {
            "id": item.id,
            "position": progress["done"] + 1,
            "texts": [
                {"revision": text.revision, "source": text.source, "text": text.text} for text in texts if text.text
            ],
        },
    }


async def item_document(db: AsyncSession, store: ObjectStore, actor: Actor, item_id: str) -> str:
    item = await reviewer_item(db, actor, item_id)
    if item.status != "open":
        raise Conflict("this note has already been coded")
    return await pdf_link(db, store, actor, item.note_id)


async def submit_answer(
    db: AsyncSession, actor: Actor, item_id: str, answer: ClaimElements, icd: IcdCatalog
) -> AuditSample:
    item = await reviewer_item(db, actor, item_id)
    if item.status != "open":
        raise Conflict("this note has already been coded")
    note = await db.get_one(Note, item.note_id)
    check_answer(answer, icd.for_service_date(note.service_date))
    reference = item.result["reference"]
    suggested = elements_of(Code.from_json(code) for code in reference["bodha"])
    final = elements_of(Code.from_json(code) for code in reference["claim"])
    item.answer = {**answer.as_json(), "submitted_at": utcnow().isoformat()}
    item.result = {
        **item.result,
        "bodha": compare_elements(answer, suggested),
        "claim": compare_elements(answer, final),
    }
    item.status, item.completed_at = "done", utcnow()
    record_access(db, actor, "coded note blind", note_id=note.id)
    await db.commit()
    return item


async def reviewer_item(db: AsyncSession, actor: Actor, item_id: str) -> AuditSample:
    item = await db.get(AuditSample, item_id)
    if item is None or item.practice_id != actor.practice_id or item.reviewer_id != actor.user.id:
        raise NotFound("item not found")
    return item


def check_answer(answer: ClaimElements, release: IcdRelease) -> None:
    if answer.em is None and not answer.icd:
        raise Invalid("enter the visit code or at least one diagnosis")
    if answer.em is not None and not is_em_code(answer.em):
        raise Invalid(f"{answer.em} is not an E/M code")
    for code in sorted(answer.icd):
        entry = release.get(code)
        if entry is None or not entry.billable:
            raise Invalid(f"{code} is not a billable ICD-10-CM code in release {release.release}")
    unknown = sorted(answer.modifiers - KNOWN_MODIFIERS)
    if unknown:
        raise Invalid(f"{', '.join(unknown)} is not a modifier Bodha checks")
