from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Client
from app.core.security import digest
from app.models import AUTH_DETAIL_LENGTH, HQ_REALM, AccessLog, Activity, AuthEvent, PracticeMembership, User
from app.services.account_lookup import normal_email
from app.services.audit_log import AGENT_LENGTH

__all__ = [
    "AUTH_EVENT_LABELS",
    "SIGN_IN_FAILED",
    "SIGNED_IN",
    "AuthEventFacts",
    "record_auth_event",
]

SIGN_IN_FAILED = "sign_in_failed"
SIGNED_IN = "signed_in"
AUTH_EVENT_LABELS = {
    SIGN_IN_FAILED: "sign-in failed",
    SIGNED_IN: "signed in",
    "password_set": "password set",
    "password_changed": "password changed",
    "two_step_on": "two-step turned on",
    "two_step_off": "two-step turned off",
    "recovery_codes_replaced": "recovery codes replaced",
    "recovery_code_used": "recovery code used",
    "signed_out": "signed out",
    "session_revoked": "sessions ended",
    "practice_switched": "practice switched",
    "sso_changed": "single sign-on changed",
    "sso_tested": "single sign-on tested",
}
UNKNOWN_PERSON = "Unknown"
ACTIVITY_DETAIL_LENGTH = 300


@dataclass(frozen=True)
class AuthEventFacts:
    client: Client
    practice_id: str | None = None
    detail: str | None = None
    email: str | None = None
    realm: str | None = None


async def record_auth_event(db: AsyncSession, kind: str, user: User | None, facts: AuthEventFacts) -> AuthEvent:
    event = AuthEvent(
        kind=kind,
        realm=user.realm if user is not None else facts.realm,
        user_id=user.id if user is not None else None,
        practice_id=facts.practice_id,
        email_hash=digest(normal_email(facts.email)) if facts.email else None,
        detail=facts.detail[:AUTH_DETAIL_LENGTH] if facts.detail else None,
        ip=facts.client.ip,
        user_agent=(facts.client.agent or "")[:AGENT_LENGTH] or None,
    )
    db.add(event)
    if event.realm == HQ_REALM:
        _show_to_hq(db, event, user)
    elif user is not None:
        await _show_to_practices(db, event, user)
    return event


def _show_to_hq(db: AsyncSession, event: AuthEvent, user: User | None) -> None:
    where = ", ".join(part for part in (event.detail, event.ip) if part)
    db.add(
        Activity(
            actor_id=user.id if user is not None else None,
            actor_name=user.name if user is not None else UNKNOWN_PERSON,
            action=AUTH_EVENT_LABELS[event.kind],
            practice_id=None,
            detail=where[:ACTIVITY_DETAIL_LENGTH] or None,
        )
    )


async def _show_to_practices(db: AsyncSession, event: AuthEvent, user: User) -> None:
    practices = [event.practice_id] if event.practice_id else await _live_practices(db, user.id)
    for practice_id in practices:
        db.add(
            AccessLog(
                practice_id=practice_id,
                actor_kind="user",
                actor_id=user.id,
                actor_name=user.name,
                action=AUTH_EVENT_LABELS[event.kind],
                detail=event.detail,
                ip=event.ip,
                user_agent=event.user_agent,
            )
        )


async def _live_practices(db: AsyncSession, user_id: str) -> list[str]:
    rows = await db.scalars(
        select(PracticeMembership.practice_id)
        .where(PracticeMembership.user_id == user_id, PracticeMembership.ended_at.is_(None))
        .order_by(PracticeMembership.created_at)
    )
    return list(rows.all())
