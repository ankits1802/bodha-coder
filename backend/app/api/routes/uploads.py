from __future__ import annotations

from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from pydantic import BaseModel, Field, TypeAdapter, ValidationError

from app.api.bodies import PreviewBody
from app.api.wiring import Store
from app.core.deps import Actor, Db, require
from app.core.errors import Invalid
from app.core.roles import UPLOADERS
from app.services import uploads

router = APIRouter(tags=["uploads"])
Uploader = Annotated[Actor, Depends(require(*UPLOADERS))]


class FileDetail(BaseModel):
    billed: str | None = Field(default=None, max_length=500)
    visit_type: str | None = Field(default=None, max_length=40)


DETAILS = TypeAdapter(list[FileDetail])


@router.post("/uploads/preview")
async def preview(body: PreviewBody, actor: Uploader) -> list[dict[str, Any]]:
    return [
        {
            "file_name": name,
            "service_date": facts.service_date.isoformat() if facts.service_date else None,
            "patient_name": facts.patient_name,
            "cpt": facts.cpt,
        }
        for name, facts in zip(body.file_names, uploads.preview(body.file_names), strict=True)
    ]


@router.post("/uploads")
async def upload(
    *,
    db: Db,
    store: Store,
    actor: Uploader,
    provider_id: Annotated[str, Form()],
    service_date: Annotated[date, Form()],
    place_code: Annotated[str, Form(max_length=2)],
    visit_type: Annotated[str, Form(max_length=40)],
    details: Annotated[str, Form()],
    files: Annotated[list[UploadFile], File()],
) -> dict[str, Any]:
    try:
        parsed = DETAILS.validate_json(details)
    except ValidationError as error:
        raise Invalid("file details are not valid") from error
    if len(parsed) != len(files):
        raise Invalid("send one detail entry per file")
    batch = [
        uploads.UploadFile(file.filename or "document.pdf", await file.read(), detail.billed, detail.visit_type)
        for file, detail in zip(files, parsed, strict=True)
    ]
    plan = uploads.UploadPlan(provider_id, service_date, place_code, visit_type)
    result = await uploads.create_upload(db, store, actor, plan, batch)
    return {"batch_id": result.batch_id, "accepted": result.accepted, "duplicates": result.duplicates}


@router.get("/batches")
async def batches(db: Db, actor: Uploader, offset: Annotated[int, Query(ge=0)] = 0) -> dict[str, Any]:
    return await uploads.batch_history(db, actor.practice_id, offset=offset)
