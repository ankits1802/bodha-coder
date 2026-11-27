from __future__ import annotations

from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from pydantic import BaseModel, Field, TypeAdapter, ValidationError

from app.api.responses.base import ExactRoute
from app.api.responses.uploads import BatchPage, FilePreview, UploadResult
from app.api.wiring import Store
from app.core.deps import Actor, Db, require
from app.core.errors import Invalid
from app.core.roles import UPLOADERS
from app.services import upload_preview, uploads

router = APIRouter(tags=["uploads"], route_class=ExactRoute)
Uploader = Annotated[Actor, Depends(require(*UPLOADERS))]
DEFAULT_FILE_NAME = "document.pdf"


class FileDetail(BaseModel):
    billed: str | None = Field(default=None, max_length=500)
    visit_type: str | None = Field(default=None, max_length=40)
    provider_id: str | None = Field(default=None, max_length=36)
    service_date: date | None = None
    place_code: str | None = Field(default=None, max_length=2)

    def placement(self) -> uploads.FilePlacement:
        return uploads.FilePlacement(self.provider_id, self.service_date, self.place_code)


DETAILS = TypeAdapter(list[FileDetail])


@router.post("/uploads/preview", response_model=list[FilePreview])
async def preview(db: Db, actor: Uploader, files: Annotated[list[UploadFile], File()]) -> list[dict[str, Any]]:
    chosen = [upload_preview.PreviewFile(file.filename or DEFAULT_FILE_NAME, await file.read()) for file in files]
    return await upload_preview.preview_files(db, actor, chosen)


@router.post("/uploads", response_model=UploadResult)
async def upload(
    *,
    db: Db,
    store: Store,
    actor: Uploader,
    visit_type: Annotated[str, Form(max_length=40)],
    details: Annotated[str, Form()],
    files: Annotated[list[UploadFile], File()],
    provider_id: Annotated[str | None, Form()] = None,
    service_date: Annotated[date | None, Form()] = None,
    place_code: Annotated[str | None, Form(max_length=2)] = None,
) -> dict[str, Any]:
    try:
        parsed = DETAILS.validate_json(details)
    except ValidationError as error:
        raise Invalid("file details are not valid") from error
    if len(parsed) != len(files):
        raise Invalid("send one detail entry per file")
    chosen = [
        (
            uploads.UploadFile(file.filename or DEFAULT_FILE_NAME, await file.read(), detail.billed, detail.visit_type),
            detail.placement(),
        )
        for file, detail in zip(files, parsed, strict=True)
    ]
    default = uploads.FilePlacement(provider_id, service_date, place_code)
    result = await uploads.create_upload(db, store, actor, uploads.grouped_files(chosen, default, visit_type))
    return {
        "batch_id": result.batch_id,
        "batch_ids": result.batch_ids,
        "accepted": result.accepted,
        "duplicates": result.duplicates,
    }


@router.get("/batches", response_model=BatchPage)
async def batches(db: Db, actor: Uploader, offset: Annotated[int, Query(ge=0)] = 0) -> dict[str, Any]:
    return await uploads.batch_history(db, actor.practice_id, offset=offset)
