from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.sftp import FileLink, LinkRefused, SftpTarget, check_private_key
from app.core.config import get_settings
from app.core.deps import Actor
from app.core.errors import Conflict, Invalid, NotFound, Unavailable
from app.core.secret_box import SecretBox
from app.models import ClearinghouseConnection, Practice, utcnow
from app.services.audit_log import record_access, record_activity
from app.services.rate_limits import CLEARINGHOUSE_CHECKS_PER_PRACTICE, hit

__all__ = [
    "CONNECTION_REMOVED",
    "CONNECTION_SAVED",
    "CONNECTION_TESTED",
    "ClearinghouseKeyUnavailable",
    "ConnectionValues",
    "check_connection",
    "clearinghouse_view",
    "connection_box",
    "current_connection",
    "read_host_key",
    "remove_connection",
    "save_connection",
    "sftp_target",
]

CONNECTION_SAVED = "saved clearinghouse connection"
CONNECTION_REMOVED = "removed clearinghouse connection"
CONNECTION_TESTED = "tested clearinghouse connection"
HOST_KEY_READ = "read clearinghouse host key"
SFTP, PASSWORD = "sftp", "password"
DEFAULT_PORT = 22
SECRET_PREFIX = "v1:"
HOST_NAME = re.compile(r"^(?=.{1,253}$)[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9-]{1,63})*$")
CONTROL = re.compile(r"[\x00-\x1f\x7f\\]")
NO_KEY = "clearinghouse connections are not set up on this server yet"
UNREADABLE = "the saved clearinghouse password or key cannot be read on this server; save it again"


class ClearinghouseKeyUnavailable(Unavailable):
    pass


@dataclass(frozen=True)
class ConnectionValues:
    name: str
    transport: str
    usage: str
    sender_qualifier: str
    sender_id: str
    receiver_qualifier: str
    receiver_id: str
    receiver_name: str
    host: str | None = None
    port: int | None = None
    username: str | None = None
    auth_kind: str | None = None
    password: str | None = None
    private_key: str | None = None
    host_key_sha256: str | None = None
    outbound_folder: str | None = None
    inbound_folder: str | None = None


def connection_box() -> SecretBox:
    keys = get_settings().clearinghouse_encryption_key
    return SecretBox(SECRET_PREFIX, keys, ClearinghouseKeyUnavailable, NO_KEY, UNREADABLE)


async def current_connection(db: AsyncSession, practice_id: str) -> ClearinghouseConnection | None:
    query = select(ClearinghouseConnection).where(
        ClearinghouseConnection.practice_id == practice_id, ClearinghouseConnection.retired_at.is_(None)
    )
    return await db.scalar(query)


async def clearinghouse_view(db: AsyncSession, actor: Actor) -> dict[str, Any]:
    connection = await current_connection(db, actor.practice_id)
    return {
        "connection": _connection_view(connection) if connection else None,
        "encryption_ready": bool(get_settings().clearinghouse_encryption_key),
    }


async def save_connection(db: AsyncSession, actor: Actor, values: ConnectionValues) -> dict[str, Any]:
    await db.get_one(Practice, actor.practice_id, with_for_update=True, populate_existing=True)
    current = await current_connection(db, actor.practice_id)
    row = ClearinghouseConnection(
        practice_id=actor.practice_id,
        name=values.name.strip(),
        transport=values.transport,
        usage=values.usage,
        sender_qualifier=values.sender_qualifier,
        sender_id=values.sender_id.strip().upper(),
        receiver_qualifier=values.receiver_qualifier,
        receiver_id=values.receiver_id.strip().upper(),
        receiver_name=values.receiver_name.strip(),
        created_by=actor.user.id,
        **(_sftp_columns(values, current) if values.transport == SFTP else {}),
    )
    if current is not None:
        current.retired_at, current.retired_by = utcnow(), actor.user.id
        await db.flush()
    db.add(row)
    detail = f"{row.name} · {row.transport} · {row.usage}"
    record_access(db, actor, CONNECTION_SAVED, detail=detail)
    record_activity(db, actor, "clearinghouse saved", practice_id=actor.practice_id, detail=detail)
    await db.commit()
    return await clearinghouse_view(db, actor)


async def remove_connection(db: AsyncSession, actor: Actor) -> dict[str, Any]:
    await db.get_one(Practice, actor.practice_id, with_for_update=True, populate_existing=True)
    current = await current_connection(db, actor.practice_id)
    if current is None:
        raise NotFound("this practice has no clearinghouse connection")
    current.retired_at, current.retired_by = utcnow(), actor.user.id
    record_access(db, actor, CONNECTION_REMOVED, detail=current.name)
    record_activity(db, actor, "clearinghouse removed", practice_id=actor.practice_id, detail=current.name)
    await db.commit()
    return await clearinghouse_view(db, actor)


async def read_host_key(db: AsyncSession, actor: Actor, link: FileLink, host: str, port: int) -> dict[str, str]:
    await hit(db, CLEARINGHOUSE_CHECKS_PER_PRACTICE, actor.practice_id)
    fingerprint = await link.host_key(_host(host), port)
    record_access(db, actor, HOST_KEY_READ, detail=fingerprint)
    await db.commit()
    return {"host_key_sha256": fingerprint}


async def check_connection(db: AsyncSession, actor: Actor, link: FileLink) -> dict[str, bool]:
    connection = await current_connection(db, actor.practice_id)
    if connection is None:
        raise NotFound("set up the clearinghouse connection first")
    if connection.transport != SFTP or not connection.outbound_folder or not connection.inbound_folder:
        raise Conflict("a portal connection has no folders to test")
    await hit(db, CLEARINGHOUSE_CHECKS_PER_PRACTICE, actor.practice_id)
    try:
        await link.check(sftp_target(connection), [connection.outbound_folder, connection.inbound_folder])
    except (LinkRefused, Invalid) as error:
        record_access(db, actor, CONNECTION_TESTED, detail=f"failed: {error.message}"[:300])
        await db.commit()
        raise
    record_access(db, actor, CONNECTION_TESTED, detail="ok")
    await db.commit()
    return {"ok": True}


def sftp_target(connection: ClearinghouseConnection) -> SftpTarget:
    fields = (connection.host, connection.port, connection.username, connection.secret, connection.host_key_sha256)
    host, port, username, sealed, fingerprint = fields
    if connection.transport != SFTP or not host or not port or not username or not sealed or not fingerprint:
        raise Conflict("this practice's clearinghouse is not reached over SFTP")
    secret = connection_box().open(sealed)
    is_password = connection.auth_kind == PASSWORD
    return SftpTarget(
        host, port, username, secret if is_password else None, None if is_password else secret, fingerprint
    )


def _sftp_columns(values: ConnectionValues, current: ClearinghouseConnection | None) -> dict[str, Any]:
    if not values.auth_kind or not values.host_key_sha256 or not (values.username or "").strip():
        raise Invalid("an SFTP connection needs a user name, a password or key and the host key fingerprint")
    host, port = _host(values.host or ""), values.port or DEFAULT_PORT
    username = values.username.strip() if values.username else ""
    if CONTROL.search(username):
        raise Invalid("the user name holds a character it cannot hold")
    same_login = current is not None and (current.host, current.port, current.username) == (host, port, username)
    kept = current.secret if same_login and current and current.auth_kind == values.auth_kind else None
    return {
        "host": host,
        "port": port,
        "username": username,
        "auth_kind": values.auth_kind,
        "secret": _sealed_secret(values, kept),
        "host_key_sha256": values.host_key_sha256,
        "outbound_folder": _folder(values.outbound_folder, "the folder for claims"),
        "inbound_folder": _folder(values.inbound_folder, "the folder for responses"),
    }


def _sealed_secret(values: ConnectionValues, kept: str | None) -> str:
    given = values.password if values.auth_kind == PASSWORD else values.private_key
    if given:
        if values.auth_kind != PASSWORD:
            check_private_key(given)
        return connection_box().seal(given)
    if kept is None:
        raise Invalid("enter the password" if values.auth_kind == PASSWORD else "paste the private key")
    return kept


def _host(host: str) -> str:
    clean = host.strip().lower()
    try:
        ipaddress.ip_address(clean)
        return clean
    except ValueError:
        pass
    if HOST_NAME.fullmatch(clean) is None:
        raise Invalid(f"{clean or 'an empty host'} is not a host name")
    return clean


def _folder(value: str | None, label: str) -> str:
    clean = (value or "").strip()
    parts = clean.split("/")
    if not clean or CONTROL.search(clean) or ".." in parts:
        raise Invalid(f"{label} must be a folder path such as /outbound")
    return clean


def _connection_view(row: ClearinghouseConnection) -> dict[str, Any]:
    return {
        "id": row.id,
        "name": row.name,
        "transport": row.transport,
        "usage": row.usage,
        "sender_qualifier": row.sender_qualifier,
        "sender_id": row.sender_id,
        "receiver_qualifier": row.receiver_qualifier,
        "receiver_id": row.receiver_id,
        "receiver_name": row.receiver_name,
        "host": row.host,
        "port": row.port,
        "username": row.username,
        "auth_kind": row.auth_kind,
        "secret_saved": row.secret is not None,
        "host_key_sha256": row.host_key_sha256,
        "outbound_folder": row.outbound_folder,
        "inbound_folder": row.inbound_folder,
        "saved_at": row.created_at.isoformat(),
    }
