from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any
from urllib.parse import urlsplit

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.guarded_http import OutboundError, OutboundHttp, UnsafeAddress, require_https
from app.adapters.smart_backend import SmartConfiguration, discover
from app.codes.clinical_notes import NOTE_TYPES, NoteType
from app.core.calendar import zone_named
from app.core.deps import Actor
from app.core.errors import Invalid, NotFound
from app.models import (
    ACCESS_DETAIL_LENGTH,
    EHR_CLIENT_ID_LENGTH,
    EHR_SCOPES_LENGTH,
    EHR_URL_LENGTH,
    EhrConnection,
    Practice,
    utcnow,
)
from app.services.audit_log import record_access

__all__ = [
    "CONNECTION_SAVED",
    "DEFAULT_SCOPES",
    "EARLIEST_START_DAYS",
    "PULL_PAUSED",
    "PULL_RESUMED",
    "EhrSettings",
    "clean_settings",
    "connection_json",
    "latest_connection",
    "pause_pulling",
    "resume_pulling",
    "save_connection",
]

CONNECTION_SAVED = "connection saved for the EHR"
PULL_PAUSED = "pulling from the EHR paused"
PULL_RESUMED = "pulling from the EHR resumed"
DEFAULT_SCOPES = (
    "system/DocumentReference.read",
    "system/Encounter.read",
    "system/Practitioner.read",
    "system/Binary.read",
)
REQUIRED_RESOURCES = ("DocumentReference", "Encounter", "Practitioner")
READ_ACCESS = frozenset({"read", "rs", "r", "cruds", "*"})
SCOPE = re.compile(r"^system/(?P<resource>[A-Z][A-Za-z]{1,63}|\*)\.(?P<access>[a-z]{1,5}|\*)(?:\?\S{1,200})?$")
CLIENT_ID = re.compile(r"^[\x21-\x7e]+$")
MAX_SCOPES = 12
EARLIEST_START_DAYS = 730
PRIVATE_KEY_JWT = "private_key_jwt"
CLIENT_CREDENTIALS = "client_credentials"


@dataclass(frozen=True)
class EhrSettings:
    base_url: str
    client_id: str
    scopes: tuple[str, ...]
    note_types: tuple[NoteType, ...]
    start_date: date


async def latest_connection(db: AsyncSession, practice_id: str) -> EhrConnection | None:
    return await db.scalar(
        select(EhrConnection)
        .where(EhrConnection.practice_id == practice_id)
        .order_by(EhrConnection.revision.desc())
        .limit(1)
    )


def clean_settings(settings: EhrSettings, *, today: date) -> EhrSettings:
    base_url = _base_url(settings.base_url)
    client_id = settings.client_id.strip()
    if not client_id or len(client_id) > EHR_CLIENT_ID_LENGTH or CLIENT_ID.fullmatch(client_id) is None:
        raise Invalid(f"enter the client ID the EHR issued, at most {EHR_CLIENT_ID_LENGTH} characters and no spaces")
    note_types = tuple(item for item in NOTE_TYPES if item in set(settings.note_types))
    if not note_types:
        raise Invalid("choose at least one note type to pull")
    if settings.start_date > today:
        raise Invalid("the start date cannot be in the future")
    if settings.start_date < today - timedelta(days=EARLIEST_START_DAYS):
        raise Invalid(f"the start date can be at most {EARLIEST_START_DAYS} days ago")
    return EhrSettings(base_url, client_id, _scopes(settings.scopes), note_types, settings.start_date)


async def save_connection(db: AsyncSession, actor: Actor, settings: EhrSettings, http: OutboundHttp) -> None:
    practice = await db.get_one(Practice, actor.practice_id)
    cleaned = clean_settings(settings, today=utcnow().astimezone(zone_named(practice.time_zone)).date())
    configuration = await _configuration(http, cleaned.base_url)
    await db.get_one(Practice, actor.practice_id, with_for_update=True, populate_existing=True)
    previous = await latest_connection(db, actor.practice_id)
    db.add(
        EhrConnection(
            practice_id=actor.practice_id,
            revision=previous.revision + 1 if previous else 1,
            base_url=cleaned.base_url,
            token_endpoint=configuration.token_endpoint,
            client_id=cleaned.client_id,
            scopes=" ".join(cleaned.scopes),
            note_types=list(cleaned.note_types),
            start_date=cleaned.start_date,
            paused=previous.paused if previous else False,
            change="saved",
            changed_by=actor.user.id,
        )
    )
    host = urlsplit(cleaned.base_url).hostname
    detail = f"{host}, client {cleaned.client_id}, {len(cleaned.note_types)} note types from {cleaned.start_date}"
    record_access(db, actor, CONNECTION_SAVED, detail=detail[:ACCESS_DETAIL_LENGTH])
    await db.commit()


async def pause_pulling(db: AsyncSession, actor: Actor) -> None:
    await _revise(db, actor, paused=True)


async def resume_pulling(db: AsyncSession, actor: Actor) -> None:
    await _revise(db, actor, paused=False)


async def _revise(db: AsyncSession, actor: Actor, *, paused: bool) -> None:
    await db.get_one(Practice, actor.practice_id, with_for_update=True, populate_existing=True)
    previous = await latest_connection(db, actor.practice_id)
    if previous is None:
        raise NotFound("this practice has no EHR connection")
    db.add(
        EhrConnection(
            practice_id=previous.practice_id,
            revision=previous.revision + 1,
            base_url=previous.base_url,
            token_endpoint=previous.token_endpoint,
            client_id=previous.client_id,
            scopes=previous.scopes,
            note_types=list(previous.note_types),
            start_date=previous.start_date,
            paused=paused,
            change="paused" if paused else "resumed",
            changed_by=actor.user.id,
        )
    )
    record_access(db, actor, PULL_PAUSED if paused else PULL_RESUMED, detail=f"revision {previous.revision + 1}")
    await db.commit()


async def _configuration(http: OutboundHttp, base_url: str) -> SmartConfiguration:
    try:
        async with http.connect() as client:
            configuration = await discover(client, base_url)
    except UnsafeAddress as error:
        raise Invalid("the base URL must be a public https address") from error
    except OutboundError as error:
        raise Invalid(f"no SMART configuration was read from that base URL: {error.message}") from error
    if configuration.auth_methods and PRIVATE_KEY_JWT not in configuration.auth_methods:
        raise Invalid("the EHR does not accept signed client assertions (private_key_jwt)")
    if configuration.grant_types and CLIENT_CREDENTIALS not in configuration.grant_types:
        raise Invalid("the EHR does not offer system access (client_credentials)")
    return configuration


def _base_url(text: str) -> str:
    base_url = text.strip().rstrip("/")
    try:
        parts = require_https(base_url)
    except UnsafeAddress as error:
        raise Invalid("the base URL must be an https address") from error
    if parts.query or parts.fragment or len(base_url) > EHR_URL_LENGTH:
        raise Invalid(f"enter the FHIR base URL without a query, at most {EHR_URL_LENGTH} characters")
    return base_url


def _scopes(scopes: tuple[str, ...]) -> tuple[str, ...]:
    cleaned = tuple(dict.fromkeys(item.strip() for item in scopes if item.strip()))
    if not cleaned or len(cleaned) > MAX_SCOPES or len(" ".join(cleaned)) > EHR_SCOPES_LENGTH:
        raise Invalid(f"list between 1 and {MAX_SCOPES} scopes")
    matches = [SCOPE.fullmatch(item) for item in cleaned]
    unknown = [item for item, found in zip(cleaned, matches, strict=True) if found is None]
    if unknown:
        raise Invalid(f"only system scopes are used, such as system/DocumentReference.read: {unknown[0]}")
    readable = {found.group("resource") for found in matches if found and found.group("access") in READ_ACCESS}
    missing = [name for name in REQUIRED_RESOURCES if name not in readable and "*" not in readable]
    if missing:
        raise Invalid(f"the scopes must let Bodha read {', '.join(missing)}")
    return cleaned


def connection_json(connection: EhrConnection) -> dict[str, Any]:
    return {
        "base_url": connection.base_url,
        "token_endpoint": connection.token_endpoint,
        "client_id": connection.client_id,
        "scopes": connection.scopes.split(),
        "note_types": list(connection.note_types),
        "start_date": connection.start_date.isoformat(),
        "paused": connection.paused,
        "saved_at": connection.created_at.isoformat(),
    }
