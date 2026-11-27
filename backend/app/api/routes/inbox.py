from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from app.api.bodies import InboxReadBody
from app.api.responses.base import ExactRoute
from app.api.responses.inbox import InboxCount, InboxPage
from app.core.deps import Actor, Db, require
from app.core.errors import Invalid
from app.core.roles import NOTE_READERS
from app.services import inbox

router = APIRouter(prefix="/inbox", tags=["inbox"], route_class=ExactRoute)
Reader = Annotated[Actor, Depends(require(*NOTE_READERS))]


@router.get("", response_model=InboxPage)
async def items(db: Db, actor: Reader, offset: Annotated[int, Query(ge=0)] = 0) -> dict[str, Any]:
    return await inbox.inbox_page(db, actor, offset=offset)


@router.get("/count", response_model=InboxCount)
async def count(db: Db, actor: Reader) -> dict[str, int]:
    return {"unread": await inbox.unread_count(db, actor)}


@router.post("/read", response_model=InboxCount)
async def read(body: InboxReadBody, db: Db, actor: Reader) -> dict[str, int]:
    if not body.all and not body.ids:
        raise Invalid("choose the items to mark read")
    return {"unread": await inbox.mark_read(db, actor, None if body.all else body.ids)}
