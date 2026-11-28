from __future__ import annotations

import base64
import json
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import parse_qs, urlencode

import httpx

from app.adapters.guarded_http import HttpLimits, OutboundHttp

HOST = "ehr.example.com"
BASE_PATH = "/fhir/r4"
BASE = f"https://{HOST}{BASE_PATH}"
TOKEN_URL = "https://auth.example.com/oauth2/token"
PUBLIC_ADDRESS = "93.184.216.34"
LOINC = "http://loinc.org"
NPI_SYSTEM = "http://hl7.org/fhir/sid/us-npi"
ACT_CODE = "http://terminology.hl7.org/CodeSystem/v3-ActCode"
FAST = HttpLimits(spacing_seconds=0.0)


async def public_resolver(host: str, port: int) -> list[str]:
    return [PUBLIC_ADDRESS]


def resolving_to(address: str):
    async def resolve(host: str, port: int) -> list[str]:
        return [address]

    return resolve


@dataclass
class Sleeps:
    waits: list[float] = field(default_factory=list)

    async def __call__(self, seconds: float) -> None:
        self.waits.append(seconds)


@dataclass
class FakeEhr:
    documents: list[dict[str, Any]] = field(default_factory=list)
    resources: dict[str, dict[str, Any]] = field(default_factory=dict)
    binaries: dict[str, tuple[bytes, str]] = field(default_factory=dict)
    page_size: int = 50
    foreign_next: str | None = None
    token_status: int = 200
    honours_type: bool = True
    configuration: dict[str, Any] | None = None
    queued: dict[str, list[httpx.Response]] = field(default_factory=dict)
    requests: list[httpx.Request] = field(default_factory=list)
    assertions: list[str] = field(default_factory=list)
    searches: list[dict[str, list[str]]] = field(default_factory=list)
    issued: list[str] = field(default_factory=list)
    sleeps: Sleeps = field(default_factory=Sleeps)

    def outbound(self, resolver=public_resolver) -> OutboundHttp:
        return OutboundHttp(httpx.MockTransport(self.handle), resolver, self.sleeps, FAST)

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        waiting = self.queued.get(request.url.path)
        if waiting:
            return waiting.pop(0)
        if str(request.url).startswith(TOKEN_URL):
            return self._token(request)
        if request.url.host != HOST or not request.url.path.startswith(BASE_PATH):
            return httpx.Response(404)
        path = request.url.path.removeprefix(BASE_PATH).lstrip("/")
        if path == ".well-known/smart-configuration":
            return httpx.Response(200, json=self.configuration or smart_configuration())
        if request.headers.get("authorization", "").removeprefix("Bearer ") not in self.issued:
            return httpx.Response(401)
        return self._resource(request, path)

    def _resource(self, request: httpx.Request, path: str) -> httpx.Response:
        if path == "metadata":
            return _fhir({"resourceType": "CapabilityStatement", "fhirVersion": "4.0.1"})
        if path == "DocumentReference":
            return self._search(request)
        if path in self.binaries:
            data, kind = self.binaries[path]
            if "fhir+json" in request.headers.get("accept", ""):
                encoded = base64.b64encode(data).decode()
                return _fhir({"resourceType": "Binary", "contentType": kind, "data": encoded})
            return httpx.Response(200, content=data, headers={"content-type": kind})
        if path in self.resources:
            return _fhir(self.resources[path])
        return httpx.Response(404)

    def _token(self, request: httpx.Request) -> httpx.Response:
        form = {key: values[0] for key, values in parse_qs(request.content.decode()).items()}
        self.assertions.append(form.get("client_assertion", ""))
        if self.token_status != 200:
            return httpx.Response(self.token_status, json={"error": "invalid_client"})
        token = f"token-{len(self.issued) + 1}"
        self.issued.append(token)
        return httpx.Response(
            200, json={"access_token": token, "token_type": "bearer", "expires_in": 300, "scope": form.get("scope")}
        )

    def _search(self, request: httpx.Request) -> httpx.Response:
        query = parse_qs(request.url.query.decode(), keep_blank_values=True)
        page = int(query.pop("page", ["0"])[0])
        if page == 0:
            self.searches.append(query)
        wanted = set(query.get("type", [""])[0].split(","))
        found = [item for item in self.documents if not self.honours_type or _type_of(item) in wanted]
        chunk = found[page * self.page_size : (page + 1) * self.page_size]
        bundle: dict[str, Any] = {
            "resourceType": "Bundle",
            "type": "searchset",
            "entry": [{"resource": item, "search": {"mode": "match"}} for item in chunk],
            "link": [],
        }
        if (page + 1) * self.page_size < len(found):
            following = urlencode([*_flat(query), ("page", str(page + 1))])
            link = self.foreign_next or f"{BASE}/DocumentReference?{following}"
            bundle["link"].append({"relation": "next", "url": link})
        return _fhir(bundle)


def smart_configuration(**changes: Any) -> dict[str, Any]:
    return {
        "token_endpoint": TOKEN_URL,
        "token_endpoint_auth_methods_supported": ["private_key_jwt"],
        "token_endpoint_auth_signing_alg_values_supported": ["RS384", "ES384"],
        "grant_types_supported": ["client_credentials"],
        "scopes_supported": ["system/DocumentReference.read", "system/Encounter.read"],
        **changes,
    }


def document(
    document_id: str,
    *,
    code: str = "11506-3",
    doc_status: str | None = "final",
    encounter: str | None = "Encounter/e1",
    author: str | None = "Practitioner/p1",
    content: list[dict[str, Any]] | None = None,
    version: str = "1",
) -> dict[str, Any]:
    found: dict[str, Any] = {
        "resourceType": "DocumentReference",
        "id": document_id,
        "meta": {"versionId": version, "lastUpdated": "2026-11-21T10:00:00Z"},
        "status": "current",
        "type": {"coding": [{"system": LOINC, "code": code}]},
        "subject": {"reference": "Patient/patient-1", "display": "REYES MARISOL"},
        "content": content if content is not None else [attachment("Binary/b1")],
    }
    if doc_status:
        found["docStatus"] = doc_status
    if author:
        found["author"] = [{"reference": author}]
    if encounter:
        found["context"] = {"encounter": [{"reference": encounter}]}
    return found


def attachment(url: str, content_type: str = "application/pdf", **extra: Any) -> dict[str, Any]:
    return {"attachment": {"contentType": content_type, "url": url, **extra}}


def encounter(
    encounter_id: str, start: str, *, class_code: str = "AMB", participants: tuple[str, ...] = (), **extra: Any
) -> dict[str, Any]:
    return {
        "resourceType": "Encounter",
        "id": encounter_id,
        "status": "finished",
        "class": {"system": ACT_CODE, "code": class_code},
        "period": {"start": start},
        "subject": {"reference": "Patient/patient-1"},
        "participant": [{"individual": {"reference": reference}} for reference in participants],
        **extra,
    }


def practitioner(practitioner_id: str, npi: str) -> dict[str, Any]:
    return {
        "resourceType": "Practitioner",
        "id": practitioner_id,
        "identifier": [{"system": NPI_SYSTEM, "value": npi}],
        "name": [{"family": "Varga", "given": ["Elena"]}],
    }


def _fhir(body: dict[str, Any]) -> httpx.Response:
    return httpx.Response(200, content=json.dumps(body).encode(), headers={"content-type": "application/fhir+json"})


def _type_of(item: dict[str, Any]) -> str:
    coding = item["type"]["coding"][0]
    return f"{coding['system']}|{coding['code']}"


def _flat(query: dict[str, list[str]]) -> list[tuple[str, str]]:
    return [(key, value) for key, values in query.items() for value in values]
