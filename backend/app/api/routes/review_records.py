from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from app.api.blinding import SightedReader, sighted
from app.api.bodies import CommentBody
from app.api.responses.base import ExactRoute, attachment, file_download
from app.api.responses.review_records import CommentPerson, NoteComment, NoteComments
from app.api.wiring import Mail, Store
from app.core.deps import Actor, Db, require
from app.core.roles import COMPLIANCE, NOTE_READERS
from app.services import audit_package, review_comments

router = APIRouter(tags=["review records"], route_class=ExactRoute)
Reader = Annotated[Actor, Depends(require(*NOTE_READERS))]
Auditor = Annotated[Actor, Depends(sighted(*COMPLIANCE))]


@router.get("/notes/{note_id}/comments", response_model=NoteComments)
async def comments(note_id: str, db: Db, actor: SightedReader, removed: bool = False) -> dict[str, Any]:
    return {"items": await review_comments.note_comments(db, actor, note_id, include_removed=removed)}


@router.post("/notes/{note_id}/comments", response_model=NoteComment)
async def comment(note_id: str, body: CommentBody, db: Db, mail: Mail, actor: SightedReader) -> dict[str, Any]:
    draft = review_comments.CommentDraft(body.finding_key, body.body, tuple(body.mentions))
    return await review_comments.post_comment(db, mail, actor, note_id, draft)


@router.post("/comments/{comment_id}/remove", response_model=NoteComment)
async def remove_comment(comment_id: str, db: Db, actor: Reader) -> dict[str, Any]:
    return await review_comments.remove_comment(db, actor, comment_id)


@router.get("/comments/people", response_model=list[CommentPerson])
async def people(db: Db, actor: Reader) -> list[dict[str, str]]:
    return await review_comments.comment_people(db, actor)


@router.post("/notes/{note_id}/audit-package", **file_download("application/zip"))
async def package(note_id: str, db: Db, store: Store, actor: Auditor) -> Response:
    built = await audit_package.audit_package(db, store, actor, note_id)
    return attachment(built.content, "application/zip", built.file_name)
