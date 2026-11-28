from __future__ import annotations

import asyncio
import secrets
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.smart_backend import SmartClient, new_key_pair
from app.core.config import get_settings
from app.core.deps import Actor
from app.core.errors import Conflict, Invalid, NotFound
from app.core.sealed_text import TextSeal
from app.models import EHR_KEY_ALGORITHMS, EhrConnection, EhrKey, Practice, utcnow
from app.services.audit_log import record_access

__all__ = [
    "JWKS_PATH",
    "KEY_CREATED",
    "KEY_REPLACED",
    "NOT_SET_UP",
    "create_key",
    "current_key",
    "ehr_ready",
    "ehr_seal",
    "jwks_url",
    "key_id_of",
    "published_keys",
    "smart_client",
]

KEY_CREATED = "connection key created for the EHR"
KEY_REPLACED = "connection key replaced for the EHR"
NOT_SET_UP = "the EHR connection is not set up for Bodha yet"
JWKS_PATH = "/api/ehr/jwks"
KEY_SET_BYTES = 16


def ehr_seal() -> TextSeal:
    return TextSeal(
        get_settings().ehr_key_encryption_key,
        not_set_up=NOT_SET_UP,
        unreadable="this practice's EHR key cannot be read on this server",
    )


def ehr_ready() -> bool:
    return ehr_seal().ready


def jwks_url(key_set: str) -> str:
    return f"{get_settings().app_url.rstrip('/')}{JWKS_PATH}/{key_set}"


async def current_key(db: AsyncSession, practice_id: str) -> EhrKey | None:
    return await db.scalar(select(EhrKey).where(EhrKey.practice_id == practice_id, EhrKey.retired_at.is_(None)))


async def create_key(db: AsyncSession, actor: Actor, algorithm: str) -> None:
    if algorithm not in EHR_KEY_ALGORITHMS:
        raise Invalid(f"choose one of {', '.join(EHR_KEY_ALGORITHMS)}")
    seal = ehr_seal()
    if not seal.ready:
        raise Conflict(NOT_SET_UP)
    await db.get_one(Practice, actor.practice_id, with_for_update=True, populate_existing=True)
    previous = await current_key(db, actor.practice_id)
    pair = await asyncio.to_thread(new_key_pair, algorithm)
    if previous is not None:
        previous.retired_at, previous.retired_by = utcnow(), actor.user.id
        await db.flush()
    db.add(
        EhrKey(
            practice_id=actor.practice_id,
            key_set=previous.key_set if previous else secrets.token_hex(KEY_SET_BYTES),
            algorithm=algorithm,
            public_jwk=pair.public_jwk,
            private_key=seal.seal(pair.private_pem),
            created_by=actor.user.id,
        )
    )
    action = KEY_REPLACED if previous else KEY_CREATED
    record_access(db, actor, action, detail=f"{algorithm} key {pair.kid}")
    await db.commit()


async def published_keys(db: AsyncSession, key_set: str) -> dict[str, Any]:
    keys = (
        await db.scalars(
            select(EhrKey)
            .join(Practice, Practice.id == EhrKey.practice_id)
            .where(EhrKey.key_set == key_set, EhrKey.retired_at.is_(None), Practice.purged_at.is_(None))
        )
    ).all()
    if not keys:
        raise NotFound("key set not found")
    return {"keys": [dict(key.public_jwk) for key in keys]}


def key_id_of(key: EhrKey) -> str:
    return str(key.public_jwk["kid"])


def smart_client(connection: EhrConnection, key: EhrKey) -> SmartClient:
    return SmartClient(
        client_id=connection.client_id,
        token_endpoint=connection.token_endpoint,
        scopes=connection.scopes,
        kid=key_id_of(key),
        algorithm=key.algorithm,
        private_pem=ehr_seal().open(key.private_key),
    )
