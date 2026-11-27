from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.api.quality_bodies import BlindAnswerBody, TrainingBody
from app.api.responses.base import Created, DocumentLink, ExactRoute
from app.api.responses.quality import SampleList
from app.api.responses.training import BlindStep, BlindSubmitted, TrainingFeedback, TrainingOverview
from app.api.wiring import Icd, Store
from app.core.deps import Actor, Db, require
from app.core.roles import ADMINS, NOTE_READERS
from app.services import audit_samples, blind_review, training
from app.services.agreement import elements_from_json
from app.services.audit_samples import SampleRequest

router = APIRouter(tags=["quality"], route_class=ExactRoute)
Reviewer = Annotated[Actor, Depends(require(*NOTE_READERS))]
Admin = Annotated[Actor, Depends(require(*ADMINS))]


@router.get("/blind-review/{sample_id}/next", response_model=BlindStep)
async def next_item(sample_id: str, db: Db, actor: Reviewer) -> dict[str, Any]:
    return await blind_review.next_item(db, actor, sample_id)


@router.get("/blind-review/items/{item_id}/document", response_model=DocumentLink)
async def document(item_id: str, db: Db, actor: Reviewer, store: Store) -> dict[str, str]:
    return {"url": await blind_review.item_document(db, store, actor, item_id)}


@router.post("/blind-review/items/{item_id}/answer", response_model=BlindSubmitted)
async def answer(item_id: str, body: BlindAnswerBody, db: Db, actor: Reviewer, icd: Icd) -> dict[str, Any]:
    item = await blind_review.submit_answer(db, actor, item_id, elements_from_json(body.model_dump()), icd)
    return {"id": item.id, "status": item.status, "purpose": item.purpose}


@router.get("/blind-review/items/{item_id}/feedback", response_model=TrainingFeedback)
async def feedback(item_id: str, db: Db, actor: Reviewer) -> dict[str, Any]:
    return await training.training_feedback(db, actor, item_id)


@router.get("/training", response_model=TrainingOverview)
async def my_training(db: Db, actor: Reviewer) -> dict[str, Any]:
    return await training.my_training(db, actor)


@router.get("/training/sets", response_model=SampleList)
async def training_sets(db: Db, actor: Admin) -> dict[str, Any]:
    return {"items": await audit_samples.samples_overview(db, actor, "training")}


@router.post("/training/sets", response_model=Created)
async def assign_training(body: TrainingBody, db: Db, actor: Admin) -> dict[str, str]:
    request = SampleRequest(
        purpose="training",
        scope="provider" if body.provider_id else "practice",
        start=body.start,
        end=body.end,
        reviewer_ids=(body.trainee_id,),
        size=body.size,
        provider_id=body.provider_id,
    )
    return {"id": await audit_samples.draw_sample(db, actor, request)}
