from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from pydantic import Field

from app.api.blinding import SightedReader
from app.api.bodies import Body
from app.api.responses.base import ExactRoute
from app.api.responses.claims import ClaimChecks, ClaimLinesExport
from app.core.deps import Actor, Db, require
from app.core.roles import BILLERS
from app.models import utcnow
from app.services import claim_checks, claim_lines

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
async def lines(body: ClaimLinesBody, db: Db, actor: Biller) -> Response | dict[str, Any]:
    claims = await claim_lines.claim_lines(db, actor, body.note_ids)
    if body.format == "json":
        return claim_lines.claims_json(claims)
    name = f"bodha-claim-lines-{utcnow():%Y%m%d-%H%M}.csv"
    return Response(
        claim_lines.claims_csv(claims),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )


@router.get("/notes/{note_id}/claim-checks", response_model=ClaimChecks)
async def checks(note_id: str, db: Db, actor: SightedReader) -> dict[str, Any]:
    return await claim_checks.claim_checks(db, actor, note_id)
