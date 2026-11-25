from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.api.bodies import AskBody, BilledBody, BulkApproveBody, ComplianceBody, DecisionsBody, FlagBody, RetryBody
from app.api.wiring import Icd, Mail, Store
from app.core.deps import Actor, Db, require
from app.core.roles import APPROVERS, ASKERS, COMPLIANCE, DECIDERS, NOTE_READERS, UPLOADERS
from app.services import addenda, note_view, review_actions

router = APIRouter(prefix="/notes", tags=["notes"])
Reader = Annotated[Actor, Depends(require(*NOTE_READERS))]
Decider = Annotated[Actor, Depends(require(*DECIDERS))]
Approver = Annotated[Actor, Depends(require(*APPROVERS))]


@router.get("/{note_id}")
async def detail(note_id: str, db: Db, actor: Reader) -> dict[str, Any]:
    return await note_view.note_detail(db, actor, note_id)


@router.get("/{note_id}/document")
async def document(note_id: str, db: Db, actor: Reader, store: Store) -> dict[str, str]:
    return {"url": await note_view.pdf_link(db, store, actor, note_id)}


@router.put("/{note_id}/decisions")
async def decide(note_id: str, body: DecisionsBody, db: Db, actor: Decider) -> dict[str, Any]:
    await review_actions.decide(db, actor, note_id, body.choices)
    return await note_view.note_detail(db, actor, note_id)


@router.put("/{note_id}/billed-codes")
async def billed_codes(note_id: str, body: BilledBody, db: Db, actor: Decider, icd: Icd) -> dict[str, Any]:
    await review_actions.update_billed(db, actor, note_id, body.codes, icd)
    return await note_view.note_detail(db, actor, note_id)


@router.post("/{note_id}/approve")
async def approve(note_id: str, db: Db, actor: Approver) -> dict[str, str]:
    note = await review_actions.approve(db, actor, note_id)
    return {"status": note.status}


@router.post("/approve")
async def approve_many(body: BulkApproveBody, db: Db, actor: Approver) -> dict[str, list[str]]:
    return {"approved": await review_actions.approve_many(db, actor, body.note_ids)}


@router.post("/{note_id}/flag")
async def flag(note_id: str, body: FlagBody, db: Db, actor: Decider) -> dict[str, str | None]:
    note = await review_actions.flag(db, actor, note_id, body.reason)
    return {"lane": note.lane}


@router.post("/{note_id}/compliance")
async def compliance(
    note_id: str, body: ComplianceBody, db: Db, actor: Annotated[Actor, Depends(require(*COMPLIANCE))]
) -> dict[str, str | None]:
    note = await review_actions.compliance_decision(db, actor, note_id, decision=body.decision, reason=body.reason)
    return {"status": note.status, "lane": note.lane}


@router.post("/{note_id}/reopen")
async def reopen(note_id: str, db: Db, actor: Approver) -> dict[str, str]:
    note = await review_actions.reopen(db, actor, note_id)
    return {"status": note.status}


@router.post("/retry")
async def retry_failed(
    body: RetryBody, db: Db, actor: Annotated[Actor, Depends(require(*UPLOADERS))]
) -> dict[str, list[str]]:
    return {"queued": await review_actions.retry_failed(db, actor, body.note_ids)}


@router.post("/{note_id}/retry")
async def retry(note_id: str, db: Db, actor: Annotated[Actor, Depends(require(*UPLOADERS))]) -> dict[str, str]:
    note = await review_actions.retry(db, actor, note_id)
    return {"status": note.status}


@router.post("/{note_id}/ask")
async def ask(
    note_id: str, body: AskBody, db: Db, mail: Mail, actor: Annotated[Actor, Depends(require(*ASKERS))]
) -> dict[str, str]:
    edits = [addenda.QuestionEdit(question.key, question.text) for question in body.questions]
    request = await addenda.create_request(db, mail, actor, note_id, edits=edits, channel=body.channel, hold=body.hold)
    return {"request_id": request.id}


@router.post("/{note_id}/remind", status_code=204)
async def remind(note_id: str, db: Db, mail: Mail, actor: Annotated[Actor, Depends(require(*ASKERS))]) -> None:
    await addenda.remind(db, mail, actor, note_id)
