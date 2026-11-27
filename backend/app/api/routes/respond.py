from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request

from app.api.bodies import (
    CodeRequestBody,
    CodeVerifyBody,
    LevelChangeBody,
    ProviderSigningBody,
    RespondBody,
    SignatureDraftBody,
    SwitchBody,
)
from app.api.responses.base import DocumentLink, ExactRoute
from app.api.responses.respond import CodeSent, OtherRequest, ProviderRequest, ProviderToken, RespondResult
from app.api.responses.review_records import LevelChangeResult
from app.api.responses.signatures import SignatureView
from app.api.wiring import Mail, Sealer, SigningTools, Store, client_of
from app.core.config import get_settings
from app.core.deps import Db, ProviderActor, current_provider
from app.models import PlaceOfService, Practice, User
from app.services import addenda, level_changes, signatures
from app.services.attestations import attestation_for

router = APIRouter(prefix="/respond", tags=["provider"], route_class=ExactRoute)
ProviderSession = Annotated[ProviderActor, Depends(current_provider)]


def _owner(actor: ProviderActor) -> signatures.SignatureOwner:
    return signatures.SignatureOwner.provider(actor.provider_id, actor.practice_id)


def _choice(body: ProviderSigningBody) -> signatures.SignatureChoice:
    return signatures.SignatureChoice(body.signature_id, body.remember_signature)


@router.post("/code", response_model=CodeSent)
async def send_code(body: CodeRequestBody, db: Db, mail: Mail) -> dict[str, str]:
    return {"sent_to": await addenda.send_code(db, mail, body.token)}


@router.post("/verify", response_model=ProviderToken)
async def verify(body: CodeVerifyBody, db: Db, request: Request) -> dict[str, str]:
    return {"provider_token": await addenda.verify_code(db, body.token, body.code, client_of(request))}


@router.get("", response_model=ProviderRequest)
async def request_detail(db: Db, store: Store, actor: ProviderSession) -> dict[str, Any]:
    request, note, provider, texts = await addenda.provider_request(db, actor)
    remembered = await signatures.adopted_signature(db, _owner(actor))
    practice = await db.get_one(Practice, note.practice_id)
    requester = await db.get(User, request.sent_by) if request.sent_by else None
    place = await db.get(PlaceOfService, note.place_code)
    return {
        "practice_name": practice.name,
        "provider_name": f"{provider.name}, {provider.credential}",
        "status": request.status,
        "patient": {"name": note.patient_name, "age": note.patient_age, "sex": note.patient_sex},
        "service_date": note.service_date.isoformat(),
        "visit_type": note.visit_type,
        "place_code": note.place_code,
        "place_name": place.name if place else None,
        "requested_by": requester.name if requester else None,
        "requested_at": request.created_at.isoformat(),
        "answered_at": request.answered_at.isoformat() if request.answered_at else None,
        "expires_at": request.expires_at.isoformat(),
        "questions": request.questions,
        "texts": [{"revision": t.revision, "source": t.source, "text": t.text} for t in texts],
        "addendum_text": request.addendum_text,
        "purpose": request.purpose,
        "attestation": attestation_for(request.purpose),
        "level_change": await level_changes.level_view(db, request),
        "signature": await signatures.signature_card(store, remembered) if remembered else None,
    }


@router.get("/others", response_model=list[OtherRequest])
async def others(db: Db, actor: ProviderSession) -> list[dict[str, Any]]:
    return [
        {
            "id": item.id,
            "patient_name": item.patient_name,
            "service_date": item.service_date.isoformat(),
            "sent_at": item.sent_at.isoformat(),
            "questions": item.questions,
        }
        for item in await addenda.other_requests(db, actor)
    ]


@router.post("/switch", response_model=ProviderToken)
async def switch(body: SwitchBody, db: Db, actor: ProviderSession) -> dict[str, str]:
    return {"provider_token": await addenda.switch_request(db, actor, body.request_id)}


@router.get("/document", response_model=DocumentLink)
async def document(db: Db, store: Store, actor: ProviderSession) -> dict[str, str]:
    key = await addenda.provider_document_key(db, actor)
    return {"url": await store.signed_url(key, seconds=get_settings().pdf_link_seconds)}


@router.post("/signature/drafts", response_model=SignatureView)
async def signature_draft(
    body: SignatureDraftBody, db: Db, tools: SigningTools, actor: ProviderSession
) -> dict[str, Any]:
    await addenda.load_for_provider(db, actor)
    draft = signatures.SignatureDraft(body.source, body.typed_name, body.image, actor.ip, actor.user_agent)
    row = await signatures.capture(db, tools, _owner(actor), draft)
    return await signatures.signature_card(tools.store, row)


@router.post("", response_model=RespondResult)
async def respond(body: RespondBody, db: Db, signer: Sealer, actor: ProviderSession) -> dict[str, str]:
    answers = [addenda.Answer(item.key, item.choice, item.comment) for item in body.answers]
    reply = addenda.SignedAnswers(answers, body.confirmed, body.attestation, _choice(body))
    request = await addenda.answer(db, signer, actor, reply)
    return {"status": request.status, "addendum_text": request.addendum_text or ""}


@router.post("/level-change", response_model=LevelChangeResult)
async def answer_level_change(
    body: LevelChangeBody, db: Db, mail: Mail, signer: Sealer, actor: ProviderSession
) -> dict[str, str]:
    reply = level_changes.LevelAnswer(body.answer, body.comment, body.confirmed, body.attestation, _choice(body))
    request = await level_changes.answer_level_change(db, mail, signer, actor, reply)
    return {"status": request.status, "answer": body.answer}
