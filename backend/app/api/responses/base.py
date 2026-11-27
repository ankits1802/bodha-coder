from collections.abc import Callable
from typing import Annotated, Any, Literal, TypeVar

from fastapi.responses import Response
from fastapi.routing import APIRoute
from pydantic import BaseModel, ConfigDict, Field
from pydantic.json_schema import SkipJsonSchema

from app.core.roles import PRACTICE_ROLES
from app.models import LANES, NOTE_STATUSES, ROLES
from app.services.payers import PLAN_TYPES

__all__ = [
    "Channel",
    "Created",
    "DocumentLink",
    "ExactRoute",
    "Lane",
    "NoteStatus",
    "Omittable",
    "PlanType",
    "PracticeRole",
    "RequestStatus",
    "Role",
    "TextSource",
    "View",
    "file_download",
]

T = TypeVar("T")

NoteStatus = Literal[NOTE_STATUSES]
Lane = Literal[LANES]
Role = Literal[ROLES]
PracticeRole = Literal[PRACTICE_ROLES]
Channel = Literal["email", "sms"]
TextSource = Literal["document", "addendum"]
RequestStatus = Literal["sent", "answered", "expired", "cancelled"]
PlanType = Literal[PLAN_TYPES]


def _optional_key(schema: dict[str, Any]) -> None:
    schema.pop("default", None)


Omittable = Annotated[T | SkipJsonSchema[None], Field(json_schema_extra=_optional_key)]


class View(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ExactRoute(APIRoute):
    def __init__(self, path: str, endpoint: Callable[..., Any], **options: Any) -> None:
        super().__init__(path, endpoint, **{**options, "response_model_exclude_unset": True})


class Created(View):
    id: str


class DocumentLink(View):
    url: str


def file_download(media_type: str) -> dict[str, Any]:
    content = {media_type: {"schema": {"type": "string", "format": "binary"}}}
    return {"response_class": Response, "responses": {200: {"description": "A file", "content": content}}}
