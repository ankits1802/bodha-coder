from __future__ import annotations

import base64
import binascii
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode, urljoin, urlsplit

from app.adapters.guarded_http import Answer, GuardedHttp, OutboundError, TooLarge, origin_of, require_https
from app.adapters.smart_backend import AccessToken, BadAnswer, ServerFailed, SmartClient, fetch_token, json_object

__all__ = [
    "BUNDLE_LIMIT",
    "FHIR_JSON",
    "FHIR_REASONS",
    "FhirClient",
    "FhirMissing",
    "FhirRefused",
    "ForeignLink",
    "decoded_data",
    "next_link",
]

FHIR_JSON = "application/fhir+json"
JSON_TYPES = frozenset({FHIR_JSON, "application/json"})
BUNDLE_LIMIT = 10_000_000
RESOURCE_LIMIT = 2_000_000
TOKEN_MARGIN_SECONDS = 30
BINARY_OVERHEAD = 64_000
MISSING_STATUSES = frozenset({403, 404, 410})


class FhirRefused(OutboundError):
    reason = "server_refused"


class FhirMissing(OutboundError):
    reason = "missing"


class ForeignLink(OutboundError):
    reason = "foreign_link"


FHIR_REASONS = (FhirRefused.reason, ForeignLink.reason)


@dataclass
class FhirClient:
    http: GuardedHttp
    base_url: str
    client: SmartClient
    now: Callable[[], datetime] = field(default=lambda: datetime.now(UTC))
    clock: Callable[[], float] = time.monotonic
    token: AccessToken | None = field(default=None, init=False)
    token_until: float = field(default=0.0, init=False)

    def __post_init__(self) -> None:
        require_https(self.base_url)
        self.base_url = self.base_url.rstrip("/")

    async def authorize(self) -> AccessToken:
        self.token = await fetch_token(self.http, self.client, now=self.now())
        self.token_until = self.clock() + self.token.expires_in - TOKEN_MARGIN_SECONDS
        return self.token

    async def capability(self) -> dict[str, Any]:
        return await self._listing(f"{self.base_url}/metadata", "CapabilityStatement", RESOURCE_LIMIT)

    def search_url(self, resource_type: str, params: Sequence[tuple[str, str]]) -> str:
        return f"{self.base_url}/{resource_type}?{urlencode(params, safe=':|,')}"

    async def bundle(self, url: str) -> dict[str, Any]:
        return await self._listing(self.local(url), "Bundle", BUNDLE_LIMIT)

    async def read(self, reference: str, resource_type: str) -> dict[str, Any]:
        return await self.resource(self.local(reference), resource_type)

    async def attachment(self, url: str, content_type: str, *, max_bytes: int) -> tuple[bytes, str]:
        wrapped_limit = max_bytes * 4 // 3 + BINARY_OVERHEAD
        answer = await self._authorised(self.local(url), content_type or "*/*", wrapped_limit)
        if answer.status in MISSING_STATUSES:
            raise FhirMissing(f"the attachment answered {answer.status}")
        _require_success(answer)
        if answer.content_type in JSON_TYPES and content_type not in JSON_TYPES:
            return _binary_content(json_object(answer.body), max_bytes)
        if len(answer.body) > max_bytes:
            raise TooLarge(f"the attachment is larger than {max_bytes} bytes")
        return answer.body, answer.content_type

    async def resource(self, url: str, resource_type: str, *, limit: int = RESOURCE_LIMIT) -> dict[str, Any]:
        answer = await self._authorised(url, FHIR_JSON, limit)
        if answer.status in MISSING_STATUSES:
            raise FhirMissing(f"{resource_type} answered {answer.status}")
        _require_success(answer)
        found = json_object(answer.body)
        if found.get("resourceType") != resource_type:
            raise BadAnswer(f"the server answered with something other than a {resource_type}")
        return found

    def local(self, reference: str) -> str:
        target = urljoin(f"{self.base_url}/", reference)
        base_path = urlsplit(self.base_url).path.rstrip("/")
        path = urlsplit(target).path
        inside = path == base_path or path.startswith(f"{base_path}/")
        if origin_of(target) != origin_of(self.base_url) or not inside:
            raise ForeignLink("a link points outside the EHR's base address")
        return target

    async def _listing(self, url: str, resource_type: str, limit: int) -> dict[str, Any]:
        try:
            return await self.resource(url, resource_type, limit=limit)
        except FhirMissing as error:
            raise FhirRefused(error.message) from error

    async def _authorised(self, url: str, accept: str, limit: int) -> Answer:
        answer = await self.http.get(url, headers=await self._headers(accept), max_bytes=limit)
        if answer.status != 401:
            return answer
        await self.authorize()
        return await self.http.get(url, headers=await self._headers(accept), max_bytes=limit)

    async def _headers(self, accept: str) -> dict[str, str]:
        if self.token is None or self.clock() >= self.token_until:
            await self.authorize()
        if self.token is None:
            raise BadAnswer("no access token")
        return {"Accept": accept, "Authorization": f"Bearer {self.token.value}"}


def next_link(bundle: Mapping[str, Any]) -> str | None:
    links = bundle.get("link")
    if not isinstance(links, list):
        return None
    for link in links:
        if isinstance(link, dict) and link.get("relation") == "next" and isinstance(link.get("url"), str):
            return link["url"]
    return None


def decoded_data(text: str, max_bytes: int) -> bytes:
    compact = "".join(text.split())
    if len(compact) > (max_bytes // 3 + 1) * 4:
        raise TooLarge(f"the attachment is larger than {max_bytes} bytes")
    try:
        data = base64.b64decode(compact, validate=True)
    except (binascii.Error, ValueError) as error:
        raise BadAnswer("the attachment data is not base64") from error
    if len(data) > max_bytes:
        raise TooLarge(f"the attachment is larger than {max_bytes} bytes")
    return data


def _binary_content(binary: dict[str, Any], max_bytes: int) -> tuple[bytes, str]:
    if binary.get("resourceType") != "Binary" or not isinstance(binary.get("data"), str):
        raise BadAnswer("the attachment is not a Binary with data")
    kind = binary.get("contentType")
    return decoded_data(binary["data"], max_bytes), kind.split(";")[0].strip().lower() if isinstance(kind, str) else ""


def _require_success(answer: Answer) -> None:
    if 400 <= answer.status < 500:
        raise FhirRefused(f"the EHR answered {answer.status}")
    if answer.status != 200:
        raise ServerFailed(f"the EHR answered {answer.status}")
