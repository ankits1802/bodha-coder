from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.api.bodies import CodeRequestBody, CodeVerifyBody, RespondBody, SwitchBody
from app.api.wiring import Mail, Store
from app.core.config import get_settings
from app.core.deps import Db, ProviderActor, current_provider
from app.models import PlaceOfService, Practice, User
from app.services import addenda

router = APIRouter(prefix="/respond", tags=["provider"])
ProviderSession = Annotated[ProviderActor, Depends(current_provider)]


@router.post("/code")
async def send_code(body: CodeRequestBody, db: Db, mail: Mail) -> dict[str, str]:
    return {"sent_to": await addenda.send_code(db, mail, body.token)}


@router.post("/verify")
async def verify(body: CodeVerifyBody, db: Db) -> dict[str, str]:
    return {"provider_token": await addenda.verify_code(db, body.token, body.code)}


@router.get("")
async def request_detail(db: Db, actor: ProviderSession) -> dict[str, Any]:
    request, note, provider, texts = await addenda.provider_request(db, actor)
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
    }


@router.get("/others")
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


@router.post("/switch")
async def switch(body: SwitchBody, db: Db, actor: ProviderSession) -> dict[str, str]:
    return {"provider_token": await addenda.switch_request(db, actor, body.request_id)}


@router.get("/document")
async def document(db: Db, store: Store, actor: ProviderSession) -> dict[str, str]:
    key = await addenda.provider_document_key(db, actor)
    return {"url": await store.signed_url(key, seconds=get_settings().pdf_link_seconds)}


@router.post("")
async def respond(body: RespondBody, db: Db, actor: ProviderSession) -> dict[str, str]:
    answers = [addenda.Answer(item.key, item.choice, item.comment) for item in body.answers]
    request = await addenda.answer(db, actor, answers, confirmed=body.confirmed)
    return {"status": request.status, "addendum_text": request.addendum_text or ""}
