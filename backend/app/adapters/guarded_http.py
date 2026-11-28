from __future__ import annotations

import asyncio
import ipaddress
import socket
import time
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from urllib.parse import SplitResult, urljoin, urlsplit

import httpx

__all__ = [
    "OUTBOUND_REASONS",
    "Answer",
    "GuardedHttp",
    "HttpLimits",
    "OutboundError",
    "OutboundHttp",
    "Redirected",
    "RemoteRateLimited",
    "Resolver",
    "TimedOut",
    "TooLarge",
    "Unreachable",
    "UnsafeAddress",
    "is_public_address",
    "origin_of",
    "require_https",
    "system_resolver",
]

RETRY_STATUSES = frozenset({429, 502, 503, 504})
REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})
MAX_REDIRECTS = 3
USER_AGENT = "Bodha Assure"

Resolver = Callable[[str, int], Awaitable[list[str]]]
Sleeper = Callable[[float], Awaitable[None]]


class OutboundError(Exception):
    reason = "unreachable"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class UnsafeAddress(OutboundError):
    reason = "unsafe_address"


class Unreachable(OutboundError):
    reason = "unreachable"


class TimedOut(OutboundError):
    reason = "timeout"


class TooLarge(OutboundError):
    reason = "too_large"


class RemoteRateLimited(OutboundError):
    reason = "rate_limited"


class Redirected(OutboundError):
    reason = "redirected"


OUTBOUND_REASONS = tuple(
    kind.reason for kind in (UnsafeAddress, Unreachable, TimedOut, TooLarge, RemoteRateLimited, Redirected)
)


@dataclass(frozen=True)
class HttpLimits:
    connect_seconds: float = 5.0
    read_seconds: float = 20.0
    attempts: int = 3
    backoff_seconds: float = 1.0
    longest_wait_seconds: float = 30.0
    spacing_seconds: float = 0.2


@dataclass(frozen=True)
class Answer:
    status: int
    headers: httpx.Headers
    body: bytes
    url: str

    @property
    def content_type(self) -> str:
        return self.headers.get("content-type", "").split(";")[0].strip().lower()


def origin_of(url: str) -> tuple[str, str, int]:
    parts = urlsplit(url)
    return parts.scheme, (parts.hostname or "").lower(), _port(parts)


def require_https(url: str) -> SplitResult:
    parts = urlsplit(url)
    if parts.scheme != "https" or not parts.hostname or parts.username is not None or parts.password is not None:
        raise UnsafeAddress("only https addresses without a user name are fetched")
    _port(parts)
    return parts


def is_public_address(address: str) -> bool:
    found = ipaddress.ip_address(address.split("%", 1)[0])
    if isinstance(found, ipaddress.IPv6Address) and found.ipv4_mapped is not None:
        found = found.ipv4_mapped
    return found.is_global and not found.is_multicast


async def system_resolver(host: str, port: int) -> list[str]:
    found = await asyncio.get_running_loop().getaddrinfo(host, port, type=socket.SOCK_STREAM)
    return [str(item[4][0]) for item in found]


@dataclass
class GuardedHttp:
    client: httpx.AsyncClient
    resolver: Resolver
    sleep: Sleeper
    limits: HttpLimits
    clock: Callable[[], float] = time.monotonic
    last_sent: float | None = field(default=None, init=False)

    async def get(self, url: str, *, headers: Mapping[str, str], max_bytes: int) -> Answer:
        for attempt in range(1, self.limits.attempts + 1):
            final = attempt == self.limits.attempts
            try:
                answer = await self._follow(url, headers, max_bytes)
            except httpx.TimeoutException as error:
                if final:
                    raise TimedOut("the server did not answer in time") from error
                await self.sleep(self._backoff(attempt))
                continue
            except httpx.TransportError as error:
                if final:
                    raise Unreachable("the server could not be reached") from error
                await self.sleep(self._backoff(attempt))
                continue
            if answer.status not in RETRY_STATUSES:
                return answer
            wait = self._retry_wait(answer, attempt, final=final)
            if final:
                return answer
            await self.sleep(wait)
        raise Unreachable("the server could not be reached")

    async def post_form(
        self, url: str, form: Mapping[str, str], *, headers: Mapping[str, str], max_bytes: int
    ) -> Answer:
        try:
            return await self._exchange("POST", url, headers, max_bytes, form)
        except httpx.TimeoutException as error:
            raise TimedOut("the server did not answer in time") from error
        except httpx.TransportError as error:
            raise Unreachable("the server could not be reached") from error

    async def _follow(self, url: str, headers: Mapping[str, str], max_bytes: int) -> Answer:
        target = url
        for _ in range(MAX_REDIRECTS + 1):
            answer = await self._exchange("GET", target, headers, max_bytes, None)
            location = answer.headers.get("location")
            if answer.status not in REDIRECT_STATUSES or not location:
                return answer
            target = urljoin(target, location)
            if origin_of(target) != origin_of(url):
                raise Redirected("the server sent us to another host")
        raise Redirected("the server redirected too many times")

    async def _exchange(
        self, method: str, url: str, headers: Mapping[str, str], max_bytes: int, form: Mapping[str, str] | None
    ) -> Answer:
        await self._check(url)
        await self._pace()
        async with self.client.stream(method, url, headers=dict(headers), data=form) as response:
            if response.status_code in REDIRECT_STATUSES:
                return Answer(response.status_code, response.headers, b"", url)
            body = await _limited_body(response, max_bytes)
            return Answer(response.status_code, response.headers, body, url)

    async def _check(self, url: str) -> None:
        parts = require_https(url)
        host = parts.hostname or ""
        addresses = [host] if _is_address(host) else await self._resolve(host, _port(parts))
        if not addresses:
            raise Unreachable("the server's name did not resolve")
        if not all(is_public_address(address) for address in addresses):
            raise UnsafeAddress("the server's address is not a public internet address")

    async def _resolve(self, host: str, port: int) -> list[str]:
        try:
            return await self.resolver(host, port)
        except OSError as error:
            raise Unreachable("the server's name did not resolve") from error

    async def _pace(self) -> None:
        if self.last_sent is not None:
            wait = self.last_sent + self.limits.spacing_seconds - self.clock()
            if wait > 0:
                await self.sleep(wait)
        self.last_sent = self.clock()

    def _backoff(self, attempt: int) -> float:
        return self.limits.backoff_seconds * 2 ** (attempt - 1)

    def _retry_wait(self, answer: Answer, attempt: int, *, final: bool) -> float:
        asked = retry_after_seconds(answer.headers.get("retry-after"))
        too_long = asked is not None and asked > self.limits.longest_wait_seconds
        if answer.status == 429 and (final or too_long):
            raise RemoteRateLimited("the server asked us to slow down")
        if asked is None:
            return self._backoff(attempt)
        return min(asked, self.limits.longest_wait_seconds)


@dataclass(frozen=True)
class OutboundHttp:
    transport: httpx.AsyncBaseTransport | None = None
    resolver: Resolver = system_resolver
    sleep: Sleeper = asyncio.sleep
    limits: HttpLimits = HttpLimits()

    @asynccontextmanager
    async def connect(self) -> AsyncIterator[GuardedHttp]:
        timeout = httpx.Timeout(self.limits.read_seconds, connect=self.limits.connect_seconds)
        async with httpx.AsyncClient(
            transport=self.transport,
            timeout=timeout,
            follow_redirects=False,
            trust_env=False,
            verify=True,
            headers={"User-Agent": USER_AGENT},
        ) as client:
            yield GuardedHttp(client, self.resolver, self.sleep, self.limits)


def retry_after_seconds(value: str | None) -> float | None:
    if not value:
        return None
    text = value.strip()
    if text.isdigit():
        return float(text)
    try:
        moment = parsedate_to_datetime(text)
    except (TypeError, ValueError):
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return max(0.0, (moment - datetime.now(UTC)).total_seconds())


async def _limited_body(response: httpx.Response, max_bytes: int) -> bytes:
    declared = response.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > max_bytes:
        raise TooLarge(f"the answer is larger than {max_bytes} bytes")
    chunks: list[bytes] = []
    size = 0
    async for chunk in response.aiter_bytes():
        size += len(chunk)
        if size > max_bytes:
            raise TooLarge(f"the answer is larger than {max_bytes} bytes")
        chunks.append(chunk)
    return b"".join(chunks)


def _is_address(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return False
    return True


def _port(parts: SplitResult) -> int:
    try:
        return parts.port or 443
    except ValueError as error:
        raise UnsafeAddress("the address has a port that is not a number") from error
