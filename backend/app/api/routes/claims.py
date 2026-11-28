from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import Response
from pydantic import Field

from app.api.blinding import SightedReader
from app.api.bodies import Body
from app.api.clearinghouse_bodies import ClaimDetailsBody, ClaimSendBody
from app.api.responses.base import ExactRoute, attachment, file_download
from app.api.responses.claims import ClaimChecks, ClaimLinesExport
from app.api.responses.clearinghouse import AckUpload, ClaimDetailsView, ClaimFilePage, ClaimSent
from app.api.wiring import Link, Store
from app.core.deps import Actor, Db, require
from app.core.roles import BILLERS
from app.services import claim_acks, claim_checks, claim_details, claim_exports, claim_file_views, claim_submissions
from app.services.claim_details import DetailValues
from app.services.claim_submissions import CLAIM_CONTENT_TYPE

router = APIRouter(tags=["claims"], route_class=ExactRoute)
Biller = Annotated[Actor, Depends(require(*BILLERS))]
SUBMISSIONS = "/billing/claim-submissions"


class ClaimLinesBody(Body):
    note_ids: list[str] | None = Field(default=None, max_length=500)
    format: Literal["csv", "json"] = "json"


@router.post(
    "/billing/claim-lines",
    response_model=ClaimLinesExport,
    responses={200: {"content": {"text/csv": {"schema": {"type": "string"}}}}},
)
async def lines(body: ClaimLinesBody, db: Db, store: Store, actor: Biller) -> Response:
    exported = await claim_exports.export_claim_lines(db, store, actor, body.note_ids, as_json=body.format == "json")
    return attachment(exported.content, exported.media_type, exported.export.file_name)


@router.get("/notes/{note_id}/claim-checks", response_model=ClaimChecks)
async def checks(note_id: str, db: Db, actor: SightedReader) -> dict[str, Any]:
    return await claim_checks.claim_checks(db, actor, note_id)


@router.get("/notes/{note_id}/claim-details", response_model=ClaimDetailsView)
async def details(note_id: str, db: Db, actor: Biller) -> dict[str, Any]:
    return await claim_details.claim_details_view(db, actor, note_id)


@router.put("/notes/{note_id}/claim-details", response_model=ClaimDetailsView)
async def save_details(note_id: str, body: ClaimDetailsBody, db: Db, actor: Biller) -> dict[str, Any]:
    return await claim_details.save_claim_details(db, actor, note_id, DetailValues(**body.model_dump()))


@router.post(SUBMISSIONS, response_model=ClaimSent)
async def send(body: ClaimSendBody, db: Db, store: Store, link: Link, actor: Biller) -> dict[str, Any]:
    return await claim_submissions.send_claims(db, store, link, actor, body.note_ids)


@router.get(SUBMISSIONS, response_model=ClaimFilePage)
async def submissions(db: Db, actor: Biller, offset: Annotated[int, Query(ge=0)] = 0) -> dict[str, Any]:
    return await claim_file_views.submission_page(db, actor, offset)


@router.get(f"{SUBMISSIONS}/{{submission_id}}/file", **file_download(CLAIM_CONTENT_TYPE))
async def submission_file(submission_id: str, db: Db, store: Store, actor: Biller) -> Response:
    stored = await claim_submissions.stored_claim_file(db, store, actor, submission_id)
    return attachment(stored.content, CLAIM_CONTENT_TYPE, stored.file_name)


@router.post("/billing/claim-file", **file_download(CLAIM_CONTENT_TYPE))
async def claim_file(body: ClaimSendBody, db: Db, store: Store, actor: Biller) -> Response:
    built = await claim_submissions.download_claims(db, store, actor, body.note_ids)
    return attachment(built.content, CLAIM_CONTENT_TYPE, built.file_name)


@router.post("/billing/acknowledgments", response_model=AckUpload)
async def acknowledgment(db: Db, store: Store, actor: Biller, file: Annotated[UploadFile, File()]) -> dict[str, Any]:
    return await claim_acks.upload_ack_file(db, store, actor, await file.read())
