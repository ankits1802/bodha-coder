from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import io
import ipaddress
import posixpath
import socket
import stat
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

import paramiko

from app.core.errors import Invalid, Unavailable

__all__ = [
    "FileLink",
    "LinkRefused",
    "ParamikoLink",
    "RemoteFile",
    "SftpTarget",
    "check_private_key",
    "host_key_fingerprint",
]

FINGERPRINT_PREFIX = "SHA256:"
NOT_PUBLIC = "the clearinghouse host must resolve to public internet addresses only"
WRONG_HOST_KEY = "the clearinghouse host key does not match the one saved at setup; check it with the clearinghouse"
UNREADABLE_KEY = "the private key could not be read; paste an unencrypted OpenSSH or PEM private key"
KEY_CLASSES: tuple[type[paramiko.PKey], ...] = (paramiko.Ed25519Key, paramiko.ECDSAKey, paramiko.RSAKey)


class LinkRefused(Unavailable):
    pass


@dataclass(frozen=True)
class SftpTarget:
    host: str
    port: int
    username: str
    password: str | None
    private_key: str | None
    host_key_sha256: str


@dataclass(frozen=True)
class RemoteFile:
    name: str
    size: int
    modified: datetime


class FileLink(Protocol):
    async def host_key(self, host: str, port: int) -> str: ...

    async def check(self, target: SftpTarget, folders: Sequence[str]) -> None: ...

    async def upload(self, target: SftpTarget, folder: str, name: str, data: bytes) -> None: ...

    async def listing(self, target: SftpTarget, folder: str) -> list[RemoteFile]: ...

    async def download(
        self, target: SftpTarget, folder: str, names: Sequence[str], *, limit: int
    ) -> list[tuple[str, bytes]]: ...


def host_key_fingerprint(key_bytes: bytes) -> str:
    digest = base64.b64encode(hashlib.sha256(key_bytes).digest()).decode("ascii").rstrip("=")
    return FINGERPRINT_PREFIX + digest


def check_private_key(text: str) -> None:
    _private_key(text)


class ParamikoLink:
    def __init__(self, *, timeout_seconds: int) -> None:
        self._timeout = timeout_seconds

    async def host_key(self, host: str, port: int) -> str:
        return await asyncio.to_thread(self._fingerprint, host, port)

    async def check(self, target: SftpTarget, folders: Sequence[str]) -> None:
        await asyncio.to_thread(self._check, target, tuple(folders))

    async def upload(self, target: SftpTarget, folder: str, name: str, data: bytes) -> None:
        await asyncio.to_thread(self._upload, target, posixpath.join(folder, name), data)

    async def listing(self, target: SftpTarget, folder: str) -> list[RemoteFile]:
        return await asyncio.to_thread(self._listing, target, folder)

    async def download(
        self, target: SftpTarget, folder: str, names: Sequence[str], *, limit: int
    ) -> list[tuple[str, bytes]]:
        return await asyncio.to_thread(self._download, target, folder, tuple(names), limit)

    def _fingerprint(self, host: str, port: int) -> str:
        with _refused(), self._transport(host, port) as transport:
            return host_key_fingerprint(transport.get_remote_server_key().asbytes())

    def _check(self, target: SftpTarget, folders: tuple[str, ...]) -> None:
        with self._session(target) as client:
            for folder in folders:
                client.listdir(folder)

    def _upload(self, target: SftpTarget, path: str, data: bytes) -> None:
        with self._session(target) as client:
            client.putfo(io.BytesIO(data), path, file_size=len(data), confirm=False)

    def _listing(self, target: SftpTarget, folder: str) -> list[RemoteFile]:
        with self._session(target) as client:
            entries = client.listdir_attr(folder)
        return [
            RemoteFile(entry.filename, entry.st_size or 0, datetime.fromtimestamp(entry.st_mtime or 0, UTC))
            for entry in entries
            if entry.st_mode is not None and stat.S_ISREG(entry.st_mode)
        ]

    def _download(self, target: SftpTarget, folder: str, names: tuple[str, ...], limit: int) -> list[tuple[str, bytes]]:
        found: list[tuple[str, bytes]] = []
        with self._session(target) as client:
            for name in names:
                path = posixpath.join(folder, name)
                if (client.stat(path).st_size or 0) > limit:
                    raise Invalid(f"a clearinghouse file is larger than {limit} bytes")
                buffer = io.BytesIO()
                client.getfo(path, buffer)
                found.append((name, buffer.getvalue()))
        return found

    @contextmanager
    def _session(self, target: SftpTarget) -> Iterator[paramiko.SFTPClient]:
        with _refused(), self._transport(target.host, target.port) as transport:
            seen = host_key_fingerprint(transport.get_remote_server_key().asbytes())
            if not hmac.compare_digest(seen, target.host_key_sha256):
                raise LinkRefused(WRONG_HOST_KEY)
            _authenticate(transport, target)
            client = paramiko.SFTPClient.from_transport(transport)
            if client is None:
                raise LinkRefused("the clearinghouse did not open a file session")
            client.get_channel().settimeout(self._timeout)
            with client:
                yield client

    @contextmanager
    def _transport(self, host: str, port: int) -> Iterator[paramiko.Transport]:
        address = _public_address(host, port)
        sock = socket.create_connection(address, timeout=self._timeout)
        transport = paramiko.Transport(sock)
        transport.banner_timeout = transport.handshake_timeout = transport.auth_timeout = self._timeout
        try:
            transport.start_client(timeout=self._timeout)
            yield transport
        finally:
            transport.close()


def _authenticate(transport: paramiko.Transport, target: SftpTarget) -> None:
    if target.private_key:
        transport.auth_publickey(target.username, _private_key(target.private_key))
    elif target.password:
        transport.auth_password(target.username, target.password)
    else:
        raise LinkRefused("the clearinghouse connection has no password or key")


def _private_key(text: str) -> paramiko.PKey:
    for key_class in KEY_CLASSES:
        try:
            return key_class.from_private_key(io.StringIO(text.strip() + "\n"))
        except (paramiko.SSHException, ValueError, TypeError, IndexError):
            continue
    raise Invalid(UNREADABLE_KEY)


def _public_address(host: str, port: int) -> tuple[str, int]:
    try:
        found = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as error:
        raise LinkRefused("the clearinghouse host name does not resolve") from error
    addresses = [str(entry[4][0]) for entry in found]
    if not addresses or not all(ipaddress.ip_address(item.split("%")[0]).is_global for item in addresses):
        raise Invalid(NOT_PUBLIC)
    return addresses[0], port


@contextmanager
def _refused() -> Iterator[None]:
    try:
        yield
    except paramiko.AuthenticationException as error:
        raise LinkRefused("the clearinghouse refused the user name, password or key") from error
    except PermissionError as error:
        raise LinkRefused("the clearinghouse refused access to a folder") from error
    except FileNotFoundError as error:
        raise LinkRefused("a clearinghouse folder or file does not exist") from error
    except TimeoutError as error:
        raise LinkRefused("the clearinghouse did not answer in time") from error
    except (paramiko.SSHException, EOFError, OSError) as error:
        raise LinkRefused("the connection to the clearinghouse failed") from error
