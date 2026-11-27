from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.message_errors import MessageNotSent
from app.adapters.messenger import Messenger
from app.core.config import get_settings
from app.core.deps import Actor
from app.core.errors import Conflict, Forbidden, Invalid, NotFound
from app.core.roles import ADMINS, COMPLIANCE, NOTE_READERS
from app.models import ReviewComment, ReviewCommentRemoval, Suggestion, User
from app.services.audit_log import record_access
from app.services.review_actions import note_for

__all__ = [
    "CommentDraft",
    "comment_people",
    "comment_view",
    "mention_message",
    "note_comment_rows",
    "note_comments",
    "post_comment",
    "remove_comment",
]

logger = logging.getLogger("bodha.comments")


@dataclass(frozen=True)
class CommentDraft:
    finding_key: str | None
    body: str
    mentions: tuple[str, ...]


async def comment_people(db: AsyncSession, actor: Actor) -> list[dict[str, str]]:
    return [{"id": user.id, "name": user.name, "role": user.role} for user in await _mentionable(db, actor)]


async def note_comments(db: AsyncSession, actor: Actor, note_id: str, *, include_removed: bool) -> list[dict[str, Any]]:
    note = await note_for(db, actor, note_id)
    if include_removed and actor.user.role not in COMPLIANCE:
        raise Forbidden("your role cannot see removed comments")
    rows = await note_comment_rows(db, note.id)
    names = await _names(db, actor.practice_id)
    record_access(db, actor, "read comments", note_id=note.id)
    await db.commit()
    return [
        comment_view(comment, removal, names, actor=actor)
        for comment, removal in rows
        if include_removed or removal is None
    ]


async def post_comment(
    db: AsyncSession, messenger: Messenger, actor: Actor, note_id: str, draft: CommentDraft
) -> dict[str, Any]:
    note = await note_for(db, actor, note_id)
    body = draft.body.strip()
    if not body:
        raise Invalid("write a comment")
    await _check_finding(db, note.id, draft.finding_key)
    mentioned = await _mentioned(db, actor, draft.mentions)
    comment = ReviewComment(
        practice_id=note.practice_id,
        note_id=note.id,
        finding_key=draft.finding_key,
        body=body,
        author_id=actor.user.id,
        author_name=actor.user.name,
        author_role=actor.user.role,
        mentions=[user.id for user in mentioned],
    )
    db.add(comment)
    await db.flush()
    record_access(db, actor, "commented", note_id=note.id, detail=f"on {draft.finding_key or 'the note'}")
    if mentioned:
        record_access(db, actor, "mentioned", note_id=note.id, detail=f"{len(mentioned)} people")
    await db.commit()
    await _send_mentions(messenger, actor, note.id, [user for user in mentioned if user.id != actor.user.id])
    return comment_view(comment, None, {user.id: user.name for user in mentioned}, actor=actor)


async def remove_comment(db: AsyncSession, actor: Actor, comment_id: str) -> dict[str, Any]:
    comment = await db.get(ReviewComment, comment_id)
    if comment is None or comment.practice_id != actor.practice_id:
        raise NotFound("comment not found")
    if comment.author_id != actor.user.id and actor.user.role not in ADMINS:
        raise Forbidden("only the author or an admin can remove a comment")
    if await db.scalar(select(ReviewCommentRemoval.id).where(ReviewCommentRemoval.comment_id == comment.id)):
        raise Conflict("this comment was already removed")
    removal = ReviewCommentRemoval(
        practice_id=comment.practice_id,
        note_id=comment.note_id,
        comment_id=comment.id,
        removed_by=actor.user.id,
        remover_name=actor.user.name,
        remover_role=actor.user.role,
    )
    db.add(removal)
    await db.flush()
    record_access(db, actor, "removed comment", note_id=comment.note_id, detail=f"by {comment.author_name}")
    await db.commit()
    return comment_view(comment, removal, await _names(db, actor.practice_id), actor=actor)


async def note_comment_rows(db: AsyncSession, note_id: str) -> list[tuple[ReviewComment, ReviewCommentRemoval | None]]:
    rows = await db.execute(
        select(ReviewComment, ReviewCommentRemoval)
        .outerjoin(ReviewCommentRemoval, ReviewCommentRemoval.comment_id == ReviewComment.id)
        .where(ReviewComment.note_id == note_id)
        .order_by(ReviewComment.created_at)
    )
    return [(comment, removal) for comment, removal in rows.all()]


def comment_view(
    comment: ReviewComment,
    removal: ReviewCommentRemoval | None,
    names: Mapping[str, str],
    *,
    actor: Actor | None = None,
) -> dict[str, Any]:
    removable = actor is not None and removal is None
    removable = removable and (comment.author_id == actor.user.id or actor.user.role in ADMINS)
    return {
        "id": comment.id,
        "finding_key": comment.finding_key,
        "body": comment.body,
        "author_name": comment.author_name,
        "author_role": comment.author_role,
        "at": comment.created_at.isoformat(),
        "mentions": [{"id": user_id, "name": names.get(user_id, "")} for user_id in comment.mentions],
        "removed": None
        if removal is None
        else {"by": removal.remover_name, "role": removal.remover_role, "at": removal.created_at.isoformat()},
        "can_remove": removable,
    }


def mention_message(practice_name: str, note_id: str) -> tuple[str, str]:
    link = f"{get_settings().app_url}/notes/{note_id}?tab=history"
    return f"Mentioned at {practice_name}", f"{practice_name}: you were mentioned in a review comment. Open: {link}"


async def _mentionable(db: AsyncSession, actor: Actor) -> list[User]:
    rows = await db.scalars(
        select(User)
        .where(User.practice_id == actor.practice_id, User.status == "active", User.role.in_(NOTE_READERS))
        .order_by(User.name)
    )
    return list(rows.all())


async def _mentioned(db: AsyncSession, actor: Actor, wanted: Sequence[str]) -> list[User]:
    ids = list(dict.fromkeys(wanted))
    people = {user.id: user for user in await _mentionable(db, actor)}
    unknown = [user_id for user_id in ids if user_id not in people]
    if unknown:
        raise Invalid("mention only active people of this practice who can open notes")
    return [people[user_id] for user_id in ids]


async def _check_finding(db: AsyncSession, note_id: str, finding_key: str | None) -> None:
    if finding_key is None:
        return
    found = await db.scalar(
        select(Suggestion.id).where(Suggestion.note_id == note_id, Suggestion.key == finding_key).limit(1)
    )
    if found is None:
        raise Invalid(f"{finding_key} is not a finding of this note")


async def _names(db: AsyncSession, practice_id: str) -> dict[str, str]:
    return dict((await db.execute(select(User.id, User.name).where(User.practice_id == practice_id))).all())


async def _send_mentions(messenger: Messenger, actor: Actor, note_id: str, people: list[User]) -> None:
    subject, body = mention_message(actor.own_practice.name, note_id)
    for person in people:
        try:
            await messenger.email(person.email, subject=subject, body=body)
        except MessageNotSent:
            logger.warning("a mention email for note %s was not sent", note_id)
