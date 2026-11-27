from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.object_store import practice_prefix
from app.codes.places import setting_for
from app.core.deps import Actor
from app.core.errors import Invalid, NotFound
from app.models import PlaceOfService, Practice, Provider
from app.services.audit_log import record_activity

__all__ = [
    "DEFAULT_INBOX",
    "PROCESSED",
    "REJECTED",
    "IntakeConfig",
    "inbox_prefix",
    "intake_config",
    "intake_view",
    "save_intake",
]

DEFAULT_INBOX = "inbox"
DEFAULT_VISIT_TYPE = "Established patient"
PROCESSED = "processed"
REJECTED = "rejected"
RESERVED_FOLDERS = frozenset({PROCESSED, REJECTED})
INBOX_NAME = re.compile(r"^inbox(-[a-z0-9]{1,30})?$")
FOLDER_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,59}$")
MAX_FOLDERS = 200
MAX_VISIT_TYPE = 40


@dataclass(frozen=True)
class IntakeConfig:
    enabled: bool = False
    prefix: str = DEFAULT_INBOX
    provider_by_folder: dict[str, str] = field(default_factory=dict)
    place_code: str | None = None
    visit_type: str = DEFAULT_VISIT_TYPE

    def as_json(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "prefix": self.prefix,
            "provider_by_folder": dict(self.provider_by_folder),
            "place_code": self.place_code,
            "visit_type": self.visit_type,
        }


def intake_config(practice: Practice) -> IntakeConfig:
    stored = practice.intake or {}
    return IntakeConfig(
        enabled=bool(stored.get("enabled", False)),
        prefix=str(stored.get("prefix") or DEFAULT_INBOX),
        provider_by_folder={str(key): str(value) for key, value in (stored.get("provider_by_folder") or {}).items()},
        place_code=stored.get("place_code"),
        visit_type=str(stored.get("visit_type") or DEFAULT_VISIT_TYPE),
    )


def inbox_prefix(practice_id: str, config: IntakeConfig) -> str:
    if INBOX_NAME.fullmatch(config.prefix) is None:
        raise ValueError(f"not an inbox folder: {config.prefix!r}")
    return f"{practice_prefix(practice_id)}{config.prefix}/"


def intake_view(practice: Practice) -> dict[str, Any]:
    config = intake_config(practice)
    return {**config.as_json(), "watched_prefix": inbox_prefix(practice.id, config)}


async def save_intake(db: AsyncSession, actor: Actor, values: Mapping[str, Any]) -> dict[str, Any]:
    practice = await db.get_one(Practice, actor.practice_id, with_for_update=True, populate_existing=True)
    config = IntakeConfig(
        enabled=bool(values.get("enabled", False)),
        prefix=str(values.get("prefix") or DEFAULT_INBOX).strip().lower(),
        provider_by_folder=await _folders(db, practice.id, values.get("provider_by_folder") or {}),
        place_code=(str(values.get("place_code") or "").strip() or None),
        visit_type=str(values.get("visit_type") or DEFAULT_VISIT_TYPE).strip(),
    )
    await _check(db, config)
    practice.intake = config.as_json()
    state = "on" if config.enabled else "off"
    record_activity(
        db, actor, "intake saved", practice_id=practice.id, detail=f"{state}, {len(config.provider_by_folder)} folders"
    )
    await db.commit()
    return intake_view(practice)


async def _folders(db: AsyncSession, practice_id: str, chosen: Mapping[str, Any]) -> dict[str, str]:
    if len(chosen) > MAX_FOLDERS:
        raise Invalid(f"map at most {MAX_FOLDERS} folders")
    folders = {str(name).strip(): str(provider_id) for name, provider_id in chosen.items()}
    for name in folders:
        if FOLDER_NAME.fullmatch(name) is None or name.lower() in RESERVED_FOLDERS:
            raise Invalid(f"{name or 'a blank name'} cannot be a provider folder")
    providers = set(
        (
            await db.scalars(
                select(Provider.id).where(
                    Provider.practice_id == practice_id,
                    Provider.active.is_(True),
                    Provider.id.in_(set(folders.values())),
                )
            )
        ).all()
    )
    unknown = sorted(name for name, provider_id in folders.items() if provider_id not in providers)
    if unknown:
        raise NotFound(f"no active provider for folders: {', '.join(unknown)}")
    return dict(sorted(folders.items()))


async def _check(db: AsyncSession, config: IntakeConfig) -> None:
    if INBOX_NAME.fullmatch(config.prefix) is None:
        raise Invalid("the inbox folder must be inbox or inbox-<letters and digits>")
    if not config.visit_type or len(config.visit_type) > MAX_VISIT_TYPE:
        raise Invalid(f"choose a visit type of at most {MAX_VISIT_TYPE} characters")
    if config.place_code is not None:
        place = await db.get(PlaceOfService, config.place_code)
        if place is None or not place.active:
            raise Invalid("choose an active place of service")
        setting_for(config.place_code)
    if config.enabled and (config.place_code is None or not config.provider_by_folder):
        raise Invalid("choose a place of service and at least one provider folder before turning intake on")
