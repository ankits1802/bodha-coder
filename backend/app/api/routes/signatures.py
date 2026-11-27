from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.api.bodies import SignatureDraftBody
from app.api.responses.base import ExactRoute
from app.api.responses.signatures import MySignature, SignatureView
from app.api.wiring import SigningTools, Store
from app.core.deps import Actor, Db, require
from app.core.roles import DECIDERS
from app.services import signatures

router = APIRouter(prefix="/signature", tags=["signatures"], route_class=ExactRoute)
Signer = Annotated[Actor, Depends(require(*DECIDERS))]


def _owner(actor: Actor) -> signatures.SignatureOwner:
    return signatures.SignatureOwner.person(actor.user.id)


@router.get("", response_model=MySignature)
async def my_signature(db: Db, store: Store, actor: Signer) -> dict[str, Any]:
    found = await signatures.adopted_signature(db, _owner(actor))
    return {"signature": await signatures.signature_card(store, found) if found else None}


@router.post("/drafts", response_model=SignatureView)
async def new_draft(body: SignatureDraftBody, db: Db, tools: SigningTools, actor: Signer) -> dict[str, Any]:
    draft = signatures.SignatureDraft(body.source, body.typed_name, body.image, actor.ip, actor.user_agent)
    row = await signatures.capture(db, tools, _owner(actor), draft)
    return await signatures.signature_card(tools.store, row)


@router.post("/drafts/{signature_id}/adopt", response_model=MySignature)
async def adopt(signature_id: str, db: Db, store: Store, actor: Signer) -> dict[str, Any]:
    row = await signatures.adopt(db, _owner(actor), signature_id)
    return {"signature": await signatures.signature_card(store, row)}
