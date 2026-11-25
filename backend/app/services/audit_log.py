from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Actor, ProviderActor
from app.models import AccessLog, Activity


def record_access(
    db: AsyncSession, actor: Actor, action: str, *, note_id: str | None = None, detail: str | None = None
) -> None:
    db.add(
        AccessLog(
            practice_id=actor.practice_id,
            actor_kind="user",
            actor_id=actor.user.id,
            actor_name=actor.user.name,
            action=action,
            note_id=note_id,
            detail=detail,
            ip=actor.ip,
            user_agent=(actor.user_agent or "")[:300] or None,
        )
    )


def record_provider_access(
    db: AsyncSession, actor: ProviderActor, provider_name: str, action: str, *, note_id: str
) -> None:
    db.add(
        AccessLog(
            practice_id=actor.practice_id,
            actor_kind="provider",
            actor_id=actor.provider_id,
            actor_name=provider_name,
            action=action,
            note_id=note_id,
            ip=actor.ip,
            user_agent=(actor.user_agent or "")[:300] or None,
        )
    )


def record_activity(
    db: AsyncSession, actor: Actor | None, action: str, *, practice_id: str | None, detail: str
) -> None:
    db.add(
        Activity(
            actor_id=actor.user.id if actor else None,
            actor_name=actor.user.name if actor else "Bodha",
            action=action,
            practice_id=practice_id,
            detail=detail[:300],
        )
    )
