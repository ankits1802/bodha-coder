from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import (
    ACTIVE_PRACTICE_STATUSES,
    Client,
    PracticeAccess,
    active_membership,
    ensure_practice_open,
    needs_two_step,
)
from app.core.errors import Forbidden, Unauthorized
from app.core.security import digest, random_token
from app.models import HQ_REALM, Practice, Session, User, utcnow
from app.services.auth import SIGN_IN_AGAIN, MfaChallenge, Tokens, access_token_for, two_step_challenge
from app.services.auth_events import AuthEventFacts, record_auth_event

__all__ = ["NOT_A_MEMBER", "PRACTICE_CLOSED", "switch_practice"]

NOT_A_MEMBER = "you are not an active member of that practice"
PRACTICE_CLOSED = "that practice is not active"
SWITCH_METHOD = "a practice switch"


async def switch_practice(
    db: AsyncSession, user: User, refresh: str | None, practice_id: str, *, client: Client
) -> Tokens | MfaChallenge:
    session = await _current_session(db, user, refresh)
    standing = await _standing_in(db, user, practice_id)
    if needs_two_step(standing) and not user.mfa_enabled:
        return two_step_challenge(user, SWITCH_METHOD, standing)
    rotated = random_token()
    session.refresh_hash, session.last_used_at, session.practice_id = digest(rotated), utcnow(), practice_id
    user.last_practice_id = practice_id
    await record_auth_event(db, "practice_switched", user, AuthEventFacts(client, practice_id=practice_id))
    await db.commit()
    return Tokens(access_token_for(user, standing), rotated, user, standing)


async def _current_session(db: AsyncSession, user: User, refresh: str | None) -> Session:
    session = await db.scalar(select(Session).where(Session.refresh_hash == digest(refresh))) if refresh else None
    if session is None or session.user_id != user.id or session.revoked_at is not None:
        raise Unauthorized(SIGN_IN_AGAIN)
    if session.expires_at < utcnow():
        raise Unauthorized(SIGN_IN_AGAIN)
    return session


async def _standing_in(db: AsyncSession, user: User, practice_id: str) -> PracticeAccess:
    membership = None if user.realm == HQ_REALM else await active_membership(db, user.id, practice_id)
    if membership is None:
        raise Forbidden(NOT_A_MEMBER)
    practice = await db.get_one(Practice, practice_id)
    if practice.status not in ACTIVE_PRACTICE_STATUSES:
        raise Forbidden(PRACTICE_CLOSED)
    await ensure_practice_open(db, user, membership.role, practice)
    return PracticeAccess(practice, membership)
