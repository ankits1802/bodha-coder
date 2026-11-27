from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from pydantic import Field

from app.api.blinding import SightedReader
from app.api.bodies import Body
from app.api.responses.base import ExactRoute, attachment
from app.api.responses.claims import ClaimChecks, ClaimLinesExport
from app.api.wiring import Store
from app.core.deps import Actor, Db, require
from app.core.roles import BILLERS
from app.services import claim_checks, claim_exports

router = APIRouter(tags=["claims"], route_class=ExactRoute)
Biller = Annotated[Actor, Depends(require(*BILLERS))]


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
