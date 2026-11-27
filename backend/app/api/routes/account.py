from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.api.bodies import MfaCodeBody, PreferencesBody
from app.api.responses.auth import Preferences, RecoveryCodes, RecoveryCodeStatus, SignedInDevice
from app.api.responses.base import ExactRoute
from app.api.wiring import RefreshCookie
from app.core.deps import Actor, Db, require, session_actor
from app.core.roles import NOTE_READERS
from app.services import digests, recovery_codes, user_sessions

router = APIRouter(prefix="/auth", tags=["account"], route_class=ExactRoute)
Me = Annotated[Actor, Depends(session_actor)]
Reader = Annotated[Actor, Depends(require(*NOTE_READERS))]


@router.get("/sessions", response_model=list[SignedInDevice])
async def sessions(db: Db, actor: Me, refresh_token: RefreshCookie = None) -> list[dict[str, Any]]:
    return [
        {
            "id": device.session.id,
            "created_at": device.session.created_at.isoformat(),
            "last_used_at": device.session.last_used_at.isoformat(),
            "ip": device.session.ip,
            "user_agent": device.session.user_agent,
            "current": device.current,
        }
        for device in await user_sessions.signed_in_devices(db, actor.user, refresh_token)
    ]


@router.delete("/sessions/{session_id}", status_code=204)
async def end_session(session_id: str, db: Db, actor: Me) -> None:
    await user_sessions.end_device_session(db, actor.user, session_id)


@router.post("/sessions/end-others", status_code=204)
async def end_others(db: Db, actor: Me, refresh_token: RefreshCookie = None) -> None:
    await user_sessions.end_other_sessions(db, actor.user, refresh_token)


@router.get("/recovery-codes", response_model=RecoveryCodeStatus)
async def recovery_status(db: Db, actor: Me) -> dict[str, Any]:
    remaining = await recovery_codes.remaining_recovery_codes(db, actor.user)
    return {"enabled": actor.user.mfa_enabled, "remaining": remaining}


@router.post("/recovery-codes", response_model=RecoveryCodes)
async def new_recovery_codes(body: MfaCodeBody, db: Db, actor: Me) -> dict[str, list[str]]:
    return {"codes": list(await recovery_codes.regenerate_recovery_codes(db, actor.user, body.code))}


@router.get("/preferences", response_model=Preferences)
async def preferences(actor: Reader) -> dict[str, bool]:
    return {"notify_digest": actor.user.notify_digest}


@router.put("/preferences", response_model=Preferences)
async def save_preferences(body: PreferencesBody, db: Db, actor: Reader) -> dict[str, bool]:
    return {"notify_digest": await digests.set_digest_preference(db, actor, enabled=body.notify_digest)}
