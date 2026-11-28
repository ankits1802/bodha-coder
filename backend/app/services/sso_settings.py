from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.saml_fetch import MetadataSource, metadata_address
from app.adapters.saml_metadata import (
    MAX_CERTIFICATES,
    certificate_facts,
    checked_entity_id,
    checked_sso_url,
    normal_certificate,
    read_idp_metadata,
)
from app.core.deps import Actor
from app.core.errors import Invalid, NotFound
from app.core.roles import ADMINS
from app.models import (
    SSO_ATTRIBUTE_LENGTH,
    SSO_NEW_PERSON_ROLES,
    SSO_URL_LENGTH,
    Organization,
    Practice,
    SsoConnection,
    SsoVersion,
    User,
    utcnow,
)
from app.services.audit_log import record_activity
from app.services.auth_events import AuthEventFacts, record_auth_event
from app.services.domain_claims import ClaimScope, claims_in
from app.services.memberships import ACTIVE, active_members
from app.services.organizations import organization_admins
from app.services.rate_limits import SSO_METADATA_PER_OWNER, hit
from app.services.sso_policy import current_version, owner_practice_ids, service_provider

__all__ = [
    "SSO_CHANGED",
    "IdentityProviderValues",
    "SsoValues",
    "live_connection",
    "preview_metadata",
    "remove_sso",
    "save_sso",
    "set_up_sso",
    "sso_view",
]

SSO_CHANGED = "sso_changed"
CHANGED_ACTION = "single sign-on changed"
NOT_SET_UP = "set up single sign-on first"
HISTORY_LIMIT = 20
CONTROL = re.compile(r"[\x00-\x1f\x7f]")


@dataclass(frozen=True)
class IdentityProviderValues:
    entity_id: str
    sso_url: str
    certificates: tuple[str, ...]
    metadata_url: str | None


@dataclass(frozen=True)
class SsoValues:
    provider: IdentityProviderValues
    claim_ids: tuple[str, ...]
    email_attribute: str | None
    name_attribute: str | None
    create_people: bool
    new_person_role: str
    required: bool
    break_glass: tuple[str, ...]
    mfa_context: str | None


async def live_connection(db: AsyncSession, scope: ClaimScope) -> SsoConnection | None:
    owner = (
        SsoConnection.organization_id == scope.organization_id
        if scope.organization_id is not None
        else SsoConnection.practice_id == scope.practice_id
    )
    return await db.scalar(select(SsoConnection).where(owner, SsoConnection.removed_at.is_(None)))


async def sso_view(db: AsyncSession, scope: ClaimScope) -> dict[str, Any]:
    connection = await live_connection(db, scope)
    domains = [row for row in await claims_in(db, scope) if row["verified"]]
    return {
        "connection": await _connection_view(db, connection) if connection is not None else None,
        "domains": [
            {"claim_id": row["id"], "domain": row["domain"], "practice_name": row["practice_name"]} for row in domains
        ],
        "admins": [_admin_view(person) for person in await break_glass_candidates(db, scope)],
    }


async def set_up_sso(db: AsyncSession, actor: Actor, scope: ClaimScope) -> dict[str, Any]:
    await _lock_owner(db, scope)
    if await live_connection(db, scope) is None:
        practice_id = scope.practice_id if scope.organization_id is None else None
        db.add(SsoConnection(practice_id=practice_id, organization_id=scope.organization_id, created_by=actor.user.id))
        await _record_change(db, actor, scope, "set up")
        await db.commit()
    return await sso_view(db, scope)


async def save_sso(db: AsyncSession, actor: Actor, scope: ClaimScope, values: SsoValues) -> dict[str, Any]:
    await _lock_owner(db, scope)
    connection = await live_connection(db, scope)
    if connection is None:
        raise NotFound(NOT_SET_UP)
    columns = {
        **provider_columns(values.provider, now=utcnow()),
        **_people_columns(values),
        "claim_ids": await _claim_ids(db, scope, values),
        "break_glass": await _break_glass(db, scope, values),
    }
    previous = await current_version(db, connection.id)
    number = 1 if previous is None else previous.version + 1
    db.add(
        SsoVersion(
            connection_id=connection.id,
            version=number,
            created_by=actor.user.id,
            author_name=actor.user.name,
            **columns,
        )
    )
    await _record_change(db, actor, scope, _summary(number, columns))
    await db.commit()
    return await sso_view(db, scope)


async def remove_sso(db: AsyncSession, actor: Actor, scope: ClaimScope) -> dict[str, Any]:
    await _lock_owner(db, scope)
    connection = await live_connection(db, scope)
    if connection is None:
        raise NotFound(NOT_SET_UP)
    connection.removed_at, connection.removed_by = utcnow(), actor.user.id
    await _record_change(db, actor, scope, "removed")
    await db.commit()
    return await sso_view(db, scope)


async def preview_metadata(
    db: AsyncSession, source: MetadataSource, scope: ClaimScope, *, xml: str | None, url: str | None
) -> dict[str, Any]:
    if (xml is None) == (url is None):
        raise Invalid("upload the metadata file or give its address")
    address = None
    if url is not None:
        address = metadata_address(url)[0]
        await hit(db, SSO_METADATA_PER_OWNER, scope.organization_id or scope.practice_id)
    data = xml.encode("utf-8") if xml is not None else await source.fetch(address or "")
    parsed = read_idp_metadata(data, now=utcnow())
    values = IdentityProviderValues(parsed.entity_id, parsed.sso_url, parsed.certificates, address)
    return _provider_view(provider_columns(values, now=utcnow()))


def provider_columns(values: IdentityProviderValues, *, now: datetime) -> dict[str, Any]:
    sso_url = checked_sso_url(values.sso_url)
    metadata_url = metadata_address(values.metadata_url)[0] if values.metadata_url else None
    if len(sso_url) > SSO_URL_LENGTH or len(metadata_url or "") > SSO_URL_LENGTH:
        raise Invalid("an identity provider address is too long")
    return {
        "idp_entity_id": checked_entity_id(values.entity_id),
        "sso_url": sso_url,
        "certificates": _certificates(values.certificates, now),
        "metadata_url": metadata_url,
    }


async def break_glass_candidates(db: AsyncSession, scope: ClaimScope) -> list[User]:
    found: dict[str, User] = {}
    if scope.organization_id is not None:
        for person in await organization_admins(db, scope.organization_id):
            if person.status == ACTIVE:
                found[person.id] = person
    practice_ids = await owner_practice_ids(db, practice_id=scope.practice_id, organization_id=scope.organization_id)
    for practice_id in practice_ids:
        for person in await db.scalars(active_members(practice_id, User, roles=ADMINS)):
            found.setdefault(person.id, person)
    return sorted(found.values(), key=lambda person: (person.name, person.id))


def _certificates(given: tuple[str, ...], now: datetime) -> list[str]:
    compact: list[str] = []
    for text in given:
        certificate = normal_certificate(text)
        if certificate not in compact:
            compact.append(certificate)
    if not 1 <= len(compact) <= MAX_CERTIFICATES:
        raise Invalid(f"keep between 1 and {MAX_CERTIFICATES} signing certificates")
    if all(certificate_facts(certificate).not_after <= now for certificate in compact):
        raise Invalid("every signing certificate has expired")
    return compact


def _people_columns(values: SsoValues) -> dict[str, Any]:
    if values.create_people and values.new_person_role not in SSO_NEW_PERSON_ROLES:
        raise Invalid("people created on first sign-in cannot be admins")
    return {
        "email_attribute": _optional_text(values.email_attribute),
        "name_attribute": _optional_text(values.name_attribute),
        "create_people": values.create_people,
        "new_person_role": values.new_person_role if values.create_people else None,
        "required": values.required,
        "mfa_context": _optional_text(values.mfa_context),
    }


def _optional_text(value: str | None) -> str | None:
    text = (value or "").strip()
    if len(text) > SSO_ATTRIBUTE_LENGTH or CONTROL.search(text):
        raise Invalid(f"keep names to {SSO_ATTRIBUTE_LENGTH} characters on one line")
    return text or None


async def _claim_ids(db: AsyncSession, scope: ClaimScope, values: SsoValues) -> list[str]:
    verified = {row["id"] for row in await claims_in(db, scope) if row["verified"]}
    chosen = list(dict.fromkeys(values.claim_ids))
    if any(claim_id not in verified for claim_id in chosen):
        raise Invalid("choose domains this account has verified")
    if values.required and not chosen:
        raise Invalid("choose a domain to require single sign-on for")
    return chosen


async def _break_glass(db: AsyncSession, scope: ClaimScope, values: SsoValues) -> list[str]:
    candidates = {person.id: person for person in await break_glass_candidates(db, scope)}
    chosen = list(dict.fromkeys(values.break_glass))
    if any(user_id not in candidates for user_id in chosen):
        raise Invalid("choose break-glass accounts among the admins")
    if not values.required:
        return chosen
    if not chosen:
        raise Invalid("keep at least one break-glass admin when single sign-on is required")
    unready = [candidates[user_id].name for user_id in chosen if not _ready(candidates[user_id])]
    if unready:
        raise Invalid(f"{unready[0]} needs a password and two-step verification to be a break-glass account")
    return chosen


def _ready(person: User) -> bool:
    return bool(person.password_hash) and person.mfa_enabled


def _summary(number: int, columns: dict[str, Any]) -> str:
    role = columns["new_person_role"] or "off"
    required = "on" if columns["required"] else "off"
    domains, rescue = len(columns["claim_ids"]), len(columns["break_glass"])
    return f"version {number}: {domains} domains, required {required}, new people {role}, {rescue} break-glass"


async def _record_change(db: AsyncSession, actor: Actor, scope: ClaimScope, detail: str) -> None:
    practice_ids = await owner_practice_ids(db, practice_id=scope.practice_id, organization_id=scope.organization_id)
    for practice_id in practice_ids or [None]:
        facts = AuthEventFacts(actor.client, practice_id=practice_id, detail=detail)
        await record_auth_event(db, SSO_CHANGED, actor.user, facts)
    owner = "organization" if scope.organization_id is not None else "practice"
    record_activity(db, actor, CHANGED_ACTION, practice_id=scope.practice_id, detail=f"{detail} ({owner})")


async def _lock_owner(db: AsyncSession, scope: ClaimScope) -> None:
    if scope.organization_id is not None:
        await db.get_one(Organization, scope.organization_id, with_for_update=True, populate_existing=True)
        return
    await db.get_one(Practice, scope.practice_id, with_for_update=True, populate_existing=True)


async def _connection_view(db: AsyncSession, connection: SsoConnection) -> dict[str, Any]:
    sp = service_provider(connection.id)
    versions = list(
        await db.scalars(
            select(SsoVersion)
            .where(SsoVersion.connection_id == connection.id)
            .order_by(SsoVersion.version.desc())
            .limit(HISTORY_LIMIT)
        )
    )
    return {
        "id": connection.id,
        "service_provider": {"entity_id": sp.entity_id, "acs_url": sp.acs_url, "metadata_url": sp.entity_id},
        "current": _version_view(versions[0]) if versions else None,
        "history": [
            {"version": row.version, "saved_at": row.created_at.isoformat(), "author_name": row.author_name}
            for row in versions
        ],
    }


def _version_view(version: SsoVersion) -> dict[str, Any]:
    provider = {
        "idp_entity_id": version.idp_entity_id,
        "sso_url": version.sso_url,
        "certificates": version.certificates,
        "metadata_url": version.metadata_url,
    }
    return {
        "version": version.version,
        "identity_provider": _provider_view(provider),
        "claim_ids": list(version.claim_ids),
        "email_attribute": version.email_attribute,
        "name_attribute": version.name_attribute,
        "create_people": version.create_people,
        "new_person_role": version.new_person_role,
        "required": version.required,
        "break_glass": list(version.break_glass),
        "mfa_context": version.mfa_context,
    }


def _provider_view(columns: dict[str, Any]) -> dict[str, Any]:
    return {
        "entity_id": columns["idp_entity_id"],
        "sso_url": columns["sso_url"],
        "metadata_url": columns["metadata_url"],
        "certificates": [_certificate_view(certificate) for certificate in columns["certificates"]],
    }


def _certificate_view(certificate: str) -> dict[str, str]:
    facts = certificate_facts(certificate)
    return {
        "value": certificate,
        "subject": facts.subject,
        "expires_at": facts.not_after.isoformat(),
        "sha256": facts.sha256,
    }


def _admin_view(person: User) -> dict[str, Any]:
    return {"id": person.id, "name": person.name, "email": person.email, "ready": _ready(person)}
