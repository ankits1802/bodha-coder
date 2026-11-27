from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import NoteText

__all__ = ["current_texts", "note_texts"]


async def note_texts(db: AsyncSession, note_id: str) -> list[NoteText]:
    query = select(NoteText).where(NoteText.note_id == note_id).order_by(NoteText.revision)
    return list((await db.scalars(query)).all())


def current_texts(texts: Sequence[NoteText]) -> list[NoteText]:
    starts = [index for index, text in enumerate(texts) if text.source == "document"]
    return list(texts[starts[-1] :] if starts else texts)
