from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from app.api.responses.base import ExactRoute
from app.api.responses.signatures import SealVerification
from app.api.wiring import Sealer, Store, client_of
from app.core.deps import Db
from app.services import seal_verification

router = APIRouter(prefix="/verify", tags=["verify"], route_class=ExactRoute)


@router.get("/{code}", response_model=SealVerification)
async def verify(code: str, request: Request, db: Db, store: Store, signer: Sealer) -> dict[str, Any]:
    ip, _ = client_of(request)
    checked = await seal_verification.verify_code(db, store, signer, code, ip=ip)
    row = checked.event
    return {
        "valid": checked.valid,
        "problems": list(checked.problems),
        "code": row.code,
        "event": row.event,
        "practice_name": checked.practice_name,
        "signer_kind": row.signer_kind,
        "signer_name": row.signer_name,
        "signer_title": row.signer_title,
        "signed_at": row.signed_at.isoformat(),
        "document_sha256": row.document_sha256,
        "envelope_sha256": row.envelope_sha256,
    }
