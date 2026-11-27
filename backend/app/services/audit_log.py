from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Actor, Client, ProviderActor
from app.models import ACCESS_DETAIL_LENGTH, AccessLog, Activity, User

AGENT_LENGTH = 300


@dataclass(frozen=True)
class SystemActor:
    id: str
    name: str


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
            user_agent=(actor.user_agent or "")[:AGENT_LENGTH] or None,
        )
    )


def record_practice_access(
    db: AsyncSession, practice_id: str, user: User, action: str, *, detail: str | None, client: Client
) -> None:
    db.add(
        AccessLog(
            practice_id=practice_id,
            actor_kind="user",
            actor_id=user.id,
            actor_name=user.name,
            action=action,
            detail=detail[:ACCESS_DETAIL_LENGTH] if detail else None,
            ip=client.ip,
            user_agent=(client.agent or "")[:AGENT_LENGTH] or None,
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
            user_agent=(actor.user_agent or "")[:AGENT_LENGTH] or None,
        )
    )


def record_system_access(
    db: AsyncSession,
    actor: SystemActor,
    practice_id: str,
    action: str,
    *,
    note_id: str | None = None,
    detail: str | None = None,
) -> None:
    db.add(
        AccessLog(
            practice_id=practice_id,
            actor_kind="system",
            actor_id=actor.id,
            actor_name=actor.name,
            action=action,
            note_id=note_id,
            detail=detail,
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
