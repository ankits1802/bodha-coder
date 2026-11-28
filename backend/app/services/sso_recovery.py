from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Client
from app.core.errors import Conflict, Invalid, NotFound
from app.models import ACCESS_DETAIL_LENGTH, PRACTICE_REALM, SsoConnection, SsoVersion
from app.services.audit_log import SystemActor, record_activity, record_system_access
from app.services.auth_events import AuthEventFacts, record_auth_event
from app.services.sso_policy import current_version, owner_practice_ids
from app.services.sso_settings import CHANGED_ACTION, SSO_CHANGED

__all__ = ["SUPPORT_AUTHOR", "lift_requirement"]

SUPPORT_AUTHOR = "Bodha support"
SUPPORT = SystemActor("bodha-support", SUPPORT_AUTHOR)
REASON_MIN = 3
KEPT_COLUMNS = (
    "idp_entity_id",
    "sso_url",
    "certificates",
    "metadata_url",
    "claim_ids",
    "email_attribute",
    "name_attribute",
    "create_people",
    "new_person_role",
    "break_glass",
    "mfa_context",
)


async def lift_requirement(db: AsyncSession, connection_id: str, *, reason: str) -> int:
    why = reason.strip()
    if len(why) < REASON_MIN:
        raise Invalid("give the reason the customer asked for this")
    connection = await db.get(SsoConnection, connection_id, with_for_update=True)
    if connection is None or connection.removed_at is not None:
        raise NotFound("single sign-on connection not found")
    current = await current_version(db, connection.id)
    if current is None or not current.required:
        raise Conflict("single sign-on is not required for this connection")
    lifted = SsoVersion(
        connection_id=connection.id,
        version=current.version + 1,
        required=False,
        created_by=None,
        author_name=SUPPORT_AUTHOR,
        **{column: getattr(current, column) for column in KEPT_COLUMNS},
    )
    db.add(lifted)
    detail = f"version {lifted.version}: required off by {SUPPORT_AUTHOR}: {why}"[:ACCESS_DETAIL_LENGTH]
    practice_ids = await owner_practice_ids(
        db, practice_id=connection.practice_id, organization_id=connection.organization_id
    )
    for practice_id in practice_ids:
        record_system_access(db, SUPPORT, practice_id, CHANGED_ACTION, detail=detail)
        facts = AuthEventFacts(Client(None, None), practice_id=practice_id, detail=detail, realm=PRACTICE_REALM)
        await record_auth_event(db, SSO_CHANGED, None, facts)
    record_activity(db, None, CHANGED_ACTION, practice_id=connection.practice_id, detail=detail)
    await db.commit()
    return lifted.version
