from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Actor
from app.core.roles import ADMINS
from app.models import INBOX_KINDS, InboxItem, Note, User, utcnow
from app.services.audit_log import record_access
from app.services.memberships import active_members

__all__ = [
    "BODHA",
    "INBOX_PAGE",
    "PAYLOAD_KEYS",
    "Notice",
    "PayloadValue",
    "checked_payload",
    "inbox_page",
    "mark_read",
    "notify",
    "notify_admins",
    "unread_count",
]

INBOX_PAGE = 50
BODHA = "Bodha"
ACTOR_NAME_LENGTH = 120
PAYLOAD_TEXT_LENGTH = 64
LISTED_INBOX = "listed inbox"
PAYLOAD_KEYS: dict[str, tuple[str, ...]] = {
    "provider_answered": ("questions",),
    "level_disagreed": (),
    "request_expired": ("purpose",),
    "mentioned": ("comment_id", "on"),
    "training_assigned": ("run_id", "notes"),
    "payment_failed": ("access_until",),
    "plan_ending": ("ends_on",),
    "compliance_returned": ("reason",),
    "join_requested": ("request_id",),
    "claim_rejected": ("source", "claims"),
}
PayloadValue = str | int | bool


@dataclass(frozen=True)
class Notice:
    kind: str
    actor_name: str = BODHA
    actor_id: str | None = None
    note_id: str | None = None
    payload: Mapping[str, PayloadValue] = field(default_factory=dict)


async def notify(db: AsyncSession, practice_id: str, user_ids: Iterable[str], notice: Notice) -> list[InboxItem]:
    payload = checked_payload(notice)
    wanted = list(dict.fromkeys(user_ids))
    if not wanted:
        return []
    members = set(await db.scalars(active_members(practice_id, User.id).where(User.id.in_(wanted))))
    items = [
        InboxItem(
            user_id=user_id,
            practice_id=practice_id,
            kind=notice.kind,
            note_id=notice.note_id,
            actor_id=notice.actor_id,
            actor_name=notice.actor_name[:ACTOR_NAME_LENGTH],
            payload=payload,
        )
        for user_id in wanted
        if user_id in members
    ]
    db.add_all(items)
    return items


async def notify_admins(
    db: AsyncSession, practice_id: str, notice: Notice, *, skip: Iterable[str] = ()
) -> list[InboxItem]:
    skipped = set(skip)
    admins = await db.scalars(active_members(practice_id, User.id, roles=ADMINS))
    return await notify(db, practice_id, [user_id for user_id in admins if user_id not in skipped], notice)


def checked_payload(notice: Notice) -> dict[str, PayloadValue]:
    if notice.kind not in INBOX_KINDS:
        raise ValueError(f"{notice.kind} is not an inbox kind")
    allowed = PAYLOAD_KEYS[notice.kind]
    for key, value in notice.payload.items():
        if key not in allowed:
            raise ValueError(f"inbox payload key {key} is not allowed for {notice.kind}")
        if isinstance(value, str) and len(value) > PAYLOAD_TEXT_LENGTH:
            raise ValueError(f"inbox payload value of {key} is longer than {PAYLOAD_TEXT_LENGTH} characters")
    return dict(notice.payload)


async def inbox_page(db: AsyncSession, actor: Actor, *, offset: int) -> dict[str, Any]:
    rows = await db.execute(
        select(InboxItem, Note.patient_name, Note.service_date)
        .outerjoin(Note, and_(Note.id == InboxItem.note_id, Note.practice_id == InboxItem.practice_id))
        .where(*_mine(actor))
        .order_by(InboxItem.read_at.is_(None).desc(), InboxItem.created_at.desc(), InboxItem.id)
        .offset(offset)
        .limit(INBOX_PAGE)
    )
    items = [_item_view(item, patient, day) for item, patient, day in rows.tuples()]
    record_access(db, actor, LISTED_INBOX, detail=f"{len(items)} items from {offset}")
    await db.commit()
    total = await db.scalar(select(func.count()).select_from(InboxItem).where(*_mine(actor))) or 0
    return {
        "items": items,
        "total": total,
        "unread": await unread_count(db, actor),
        "offset": offset,
        "page_size": INBOX_PAGE,
    }


async def unread_count(db: AsyncSession, actor: Actor) -> int:
    query = select(func.count()).select_from(InboxItem).where(*_mine(actor), InboxItem.read_at.is_(None))
    return await db.scalar(query) or 0


async def mark_read(db: AsyncSession, actor: Actor, item_ids: list[str] | None) -> int:
    statement = update(InboxItem).where(*_mine(actor), InboxItem.read_at.is_(None))
    if item_ids is not None:
        statement = statement.where(InboxItem.id.in_(item_ids))
    await db.execute(statement.values(read_at=utcnow()))
    await db.commit()
    return await unread_count(db, actor)


def _mine(actor: Actor) -> tuple[Any, ...]:
    return InboxItem.user_id == actor.user.id, InboxItem.practice_id == actor.practice_id


def _item_view(item: InboxItem, patient_name: str | None, service_date: Any) -> dict[str, Any]:
    return {
        "id": item.id,
        "kind": item.kind,
        "note_id": item.note_id,
        "actor_name": item.actor_name,
        "payload": dict(item.payload),
        "patient_name": patient_name,
        "service_date": service_date.isoformat() if service_date else None,
        "created_at": item.created_at.isoformat(),
        "read_at": item.read_at.isoformat() if item.read_at else None,
    }
