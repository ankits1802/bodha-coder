from __future__ import annotations

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Analysis, Note, utcnow


async def requeue_interrupted(db: AsyncSession, analysis_id: str) -> None:
    analysis = await db.get(Analysis, analysis_id, with_for_update=True)
    if analysis is None or analysis.status != "running":
        return
    analysis.status, analysis.started_at = "queued", None
    analysis.attempts, analysis.requested_at = max(0, analysis.attempts - 1), utcnow()
    await db.execute(update(Note).where(Note.id == analysis.note_id, Note.status == "reading").values(status="queued"))
    await db.commit()


async def queue_counts(db: AsyncSession) -> tuple[int, int]:
    queued, running = (
        await db.execute(
            select(
                func.count().filter(Analysis.status == "queued", Analysis.requested_at <= utcnow()),
                func.count().filter(Analysis.status == "running"),
            ).where(Analysis.status.in_(("queued", "running")))
        )
    ).one()
    return queued, running
