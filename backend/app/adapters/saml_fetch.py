from __future__ import annotations

import asyncio
import ipaddress
import socket
from collections.abc import Awaitable, Callable
from typing import Protocol
from urllib.parse import urlsplit

import httpx

from app.adapters.saml_xml import MAX_XML_BYTES
from app.core.errors import Invalid, Unavailable

__all__ = ["HttpsMetadataSource", "MetadataSource", "metadata_address"]

TIMEOUT_SECONDS = 10
HTTPS = "https"
ACCEPT = "application/samlmetadata+xml, application/xml, text/xml"
NOT_HTTPS = "the metadata address must be an https address with a host name"
NOT_PUBLIC = "the metadata address must point to a public host"

Resolver = Callable[[str, int], Awaitable[list[str]]]


class MetadataSource(Protocol):
    async def fetch(self, url: str) -> bytes: ...


def metadata_address(url: str) -> tuple[str, str, int]:
    address = url.strip()
    parts = urlsplit(address)
    if parts.scheme != HTTPS or not parts.hostname or parts.username or parts.password:
        raise Invalid(NOT_HTTPS)
    try:
        ipaddress.ip_address(parts.hostname)
    except ValueError:
        return address, parts.hostname, parts.port or 443
    raise Invalid(NOT_HTTPS)


async def system_addresses(host: str, port: int) -> list[str]:
    found = await asyncio.get_running_loop().getaddrinfo(host, port, type=socket.SOCK_STREAM)
    return [str(entry[4][0]) for entry in found]


class HttpsMetadataSource:
    def __init__(
        self, *, resolve: Resolver = system_addresses, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        self._resolve = resolve
        self._transport = transport

    async def fetch(self, url: str) -> bytes:
        address, host, port = metadata_address(url)
        await self._refuse_private(host, port)
        try:
            return await self._download(address)
        except httpx.HTTPError as error:
            raise Unavailable("the metadata address could not be reached") from error

    async def _refuse_private(self, host: str, port: int) -> None:
        try:
            addresses = await self._resolve(host, port)
        except OSError as error:
            raise Unavailable("the metadata host could not be found") from error
        if not addresses or not all(_is_public(found) for found in addresses):
            raise Invalid(NOT_PUBLIC)

    async def _download(self, address: str) -> bytes:
        client = httpx.AsyncClient(timeout=TIMEOUT_SECONDS, follow_redirects=False, transport=self._transport)
        async with client, client.stream("GET", address, headers={"Accept": ACCEPT}) as response:
            if response.status_code != 200:
                raise Invalid(f"the metadata address answered {response.status_code}")
            return await _limited_body(response)


async def _limited_body(response: httpx.Response) -> bytes:
    body = bytearray()
    async for chunk in response.aiter_bytes():
        body.extend(chunk)
        if len(body) > MAX_XML_BYTES:
            raise Invalid("the metadata is too large")
    return bytes(body)


def _is_public(address: str) -> bool:
    try:
        return ipaddress.ip_address(address).is_global
    except ValueError:
        return False
