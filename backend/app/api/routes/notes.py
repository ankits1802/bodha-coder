from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, UploadFile

from app.api.blinding import SightedDecider, SightedReader
from app.api.bodies import (
    AskBody,
    AssignBody,
    BilledBody,
    BulkApproveBody,
    BulkReopenBody,
    ComplianceBody,
    DecisionsBody,
    FlagBody,
    PayerChoiceBody,
    PointersBody,
    RestoreNoteBody,
    RetryBody,
    VisitTypeBody,
    VoidNotesBody,
)
from app.api.responses.base import DocumentLink, ExactRoute
from app.api.responses.note_actions import (
    ApprovedNotes,
    AssignedNotes,
    ClaimPointers,
    ComplianceOutcome,
    NoteLane,
    NotePayer,
    NoteState,
    QueuedNotes,
    ReopenedNotes,
    RequestCancelled,
    RequestCreated,
    VoidedNotes,
)
from app.api.responses.notes import NoteDetail
from app.api.wiring import Icd, Mail, Store
from app.core.deps import Actor, Db, require
from app.core.roles import ADMINS, APPROVERS, ASKERS, ASSIGNERS, COMPLIANCE, DECIDERS, UPLOADERS
from app.services import addenda, assignment, claim_lines, note_changes, note_view, note_voids, review_actions
from app.services.records import NewDocument, replace_document

router = APIRouter(prefix="/notes", tags=["notes"], route_class=ExactRoute)
Decider = Annotated[Actor, Depends(require(*DECIDERS))]
Approver = Annotated[Actor, Depends(require(*APPROVERS))]


@router.get("/{note_id}", response_model=NoteDetail)
async def detail(note_id: str, db: Db, actor: SightedReader) -> dict[str, Any]:
    return await note_view.note_detail(db, actor, note_id)


@router.get("/{note_id}/document", response_model=DocumentLink)
async def document(note_id: str, db: Db, actor: SightedReader, store: Store) -> dict[str, str]:
    return {"url": await note_view.pdf_link(db, store, actor, note_id)}


@router.post("/{note_id}/document", response_model=NoteState)
async def replace_pdf(
    note_id: str,
    file: Annotated[UploadFile, File()],
    db: Db,
    store: Store,
    actor: Annotated[Actor, Depends(require(*UPLOADERS))],
) -> dict[str, str]:
    document = NewDocument(file.filename or "document.pdf", await file.read())
    note = await replace_document(db, store, actor, note_id, document)
    return {"status": note.status}


@router.put("/{note_id}/decisions", response_model=NoteDetail)
async def decide(note_id: str, body: DecisionsBody, db: Db, actor: SightedDecider) -> dict[str, Any]:
    await review_actions.decide(db, actor, note_id, body.choices)
    return await note_view.note_detail(db, actor, note_id)


@router.put("/{note_id}/billed-codes", response_model=NoteDetail)
async def billed_codes(note_id: str, body: BilledBody, db: Db, actor: SightedDecider, icd: Icd) -> dict[str, Any]:
    await review_actions.update_billed(db, actor, note_id, body.codes, icd)
    return await note_view.note_detail(db, actor, note_id)


@router.get("/{note_id}/pointers", response_model=ClaimPointers)
async def pointers(note_id: str, db: Db, actor: SightedReader) -> dict[str, Any]:
    return await claim_lines.note_pointers(db, actor, note_id)


@router.put("/{note_id}/pointers", response_model=ClaimPointers)
async def link_diagnoses(note_id: str, body: PointersBody, db: Db, actor: SightedDecider) -> dict[str, Any]:
    await review_actions.save_pointers(db, actor, note_id, [(line.code, line.pointers) for line in body.lines])
    return await claim_lines.note_pointers(db, actor, note_id)


@router.post("/{note_id}/approve", response_model=NoteState)
async def approve(note_id: str, db: Db, actor: Approver) -> dict[str, str]:
    note = await review_actions.approve(db, actor, note_id)
    return {"status": note.status}


@router.post("/approve", response_model=ApprovedNotes)
async def approve_many(body: BulkApproveBody, db: Db, actor: Approver) -> dict[str, list[str]]:
    return {"approved": await review_actions.approve_many(db, actor, body.note_ids)}


@router.post("/assign", response_model=AssignedNotes)
async def assign(
    body: AssignBody, db: Db, actor: Annotated[Actor, Depends(require(*ASSIGNERS))]
) -> dict[str, list[str]]:
    return {"assigned": await assignment.assign_notes(db, actor, body.note_ids, body.user_id)}


@router.post("/{note_id}/flag", response_model=NoteLane)
async def flag(note_id: str, body: FlagBody, db: Db, actor: Decider) -> dict[str, str | None]:
    note = await review_actions.flag(db, actor, note_id, body.reason)
    return {"lane": note.lane}


@router.post("/{note_id}/compliance", response_model=ComplianceOutcome)
async def compliance(
    note_id: str, body: ComplianceBody, db: Db, actor: Annotated[Actor, Depends(require(*COMPLIANCE))]
) -> dict[str, str | None]:
    note = await review_actions.compliance_decision(db, actor, note_id, decision=body.decision, reason=body.reason)
    return {"status": note.status, "lane": note.lane}


@router.post("/void", response_model=VoidedNotes)
async def void_notes(
    body: VoidNotesBody, db: Db, actor: Annotated[Actor, Depends(require(*UPLOADERS))]
) -> dict[str, list[str]]:
    return {"voided": await note_voids.void_notes(db, actor, body.note_ids, body.reason)}


@router.post("/{note_id}/restore", response_model=NoteState)
async def restore(
    note_id: str, body: RestoreNoteBody, db: Db, actor: Annotated[Actor, Depends(require(*ADMINS))]
) -> dict[str, str]:
    note = await note_voids.restore_note(db, actor, note_id, body.reason)
    return {"status": note.status}


@router.put("/{note_id}/visit-type", response_model=NoteState)
async def change_visit_type(
    note_id: str, body: VisitTypeBody, db: Db, actor: Annotated[Actor, Depends(require(*UPLOADERS))]
) -> dict[str, str]:
    note = await note_changes.change_visit_type(db, actor, note_id, body.visit_type)
    return {"status": note.status}


@router.put("/{note_id}/payer", response_model=NotePayer)
async def set_payer(
    note_id: str, body: PayerChoiceBody, db: Db, actor: Annotated[Actor, Depends(require(*UPLOADERS))]
) -> dict[str, str | None]:
    note = await note_changes.set_payer(db, actor, note_id, body.payer)
    return {"payer": note.payer}


@router.post("/{note_id}/cancel-request", response_model=RequestCancelled)
async def cancel_request(note_id: str, db: Db, actor: Annotated[Actor, Depends(require(*ASKERS))]) -> dict[str, str]:
    note = await note_changes.cancel_request(db, actor, note_id)
    return {"lane": note.lane or ""}


@router.post("/{note_id}/reopen", response_model=NoteState)
async def reopen(note_id: str, db: Db, actor: Approver) -> dict[str, str]:
    note = await review_actions.reopen(db, actor, note_id)
    return {"status": note.status}


@router.post("/reopen", response_model=ReopenedNotes)
async def reopen_many(body: BulkReopenBody, db: Db, actor: Approver) -> dict[str, list[str]]:
    return {"reopened": await review_actions.reopen_many(db, actor, body.note_ids)}


@router.post("/retry", response_model=QueuedNotes)
async def retry_failed(
    body: RetryBody, db: Db, actor: Annotated[Actor, Depends(require(*UPLOADERS))]
) -> dict[str, list[str]]:
    return {"queued": await review_actions.retry_failed(db, actor, body.note_ids)}


@router.post("/{note_id}/retry", response_model=NoteState)
async def retry(note_id: str, db: Db, actor: Annotated[Actor, Depends(require(*UPLOADERS))]) -> dict[str, str]:
    note = await review_actions.retry(db, actor, note_id)
    return {"status": note.status}


@router.post("/{note_id}/ask", response_model=RequestCreated)
async def ask(
    note_id: str, body: AskBody, db: Db, mail: Mail, actor: Annotated[Actor, Depends(require(*ASKERS))]
) -> dict[str, str]:
    edits = [addenda.QuestionEdit(question.key, question.text) for question in body.questions]
    request = await addenda.create_request(db, mail, actor, note_id, edits=edits, channel=body.channel, hold=body.hold)
    return {"request_id": request.id}


@router.post("/{note_id}/remind", status_code=204)
async def remind(note_id: str, db: Db, mail: Mail, actor: Annotated[Actor, Depends(require(*ASKERS))]) -> None:
    await addenda.remind(db, mail, actor, note_id)
