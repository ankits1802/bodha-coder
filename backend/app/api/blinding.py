from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends

from app.core.deps import Actor, Db, require
from app.core.roles import DECIDERS, NOTE_READERS
from app.services.blind_review import refuse_blind_note

__all__ = ["SightedDecider", "SightedReader", "sighted"]


def sighted(*roles: str) -> Callable[..., Awaitable[Actor]]:
    allowed = Depends(require(*roles))

    async def guard(note_id: str, db: Db, actor: Annotated[Actor, allowed]) -> Actor:
        await refuse_blind_note(db, actor, note_id)
        return actor

    return guard


SightedReader = Annotated[Actor, Depends(sighted(*NOTE_READERS))]
SightedDecider = Annotated[Actor, Depends(sighted(*DECIDERS))]
