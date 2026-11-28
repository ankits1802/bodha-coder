from __future__ import annotations

import base64

import httpx
import pytest

from app.adapters.fhir_client import FhirClient, FhirMissing, FhirRefused, ForeignLink, decoded_data, next_link
from app.adapters.guarded_http import TooLarge
from app.adapters.smart_backend import SmartClient, new_key_pair
from tests.ehr_fakes import BASE, TOKEN_URL, FakeEhr

PDF = b"%PDF-1.4 a visit note"


def _smart() -> SmartClient:
    pair = new_key_pair("ES384")
    return SmartClient("bodha-client", TOKEN_URL, "system/Binary.read", pair.kid, "ES384", pair.private_pem)


async def _with_client(ehr: FakeEhr, check):
    async with ehr.outbound().connect() as http:
        return await check(FhirClient(http, BASE, _smart()))


async def test_links_resolve_only_under_the_configured_base():
    async def check(client: FhirClient) -> None:
        assert client.local("Encounter/e1") == f"{BASE}/Encounter/e1"
        assert client.local(f"{BASE}?_getpages=abc") == f"{BASE}?_getpages=abc"
        for foreign in (
            "https://other.example.com/fhir/r4/Encounter/e1",
            "https://ehr.example.com/admin/Encounter/e1",
            "https://ehr.example.com/fhir/r4-other/Encounter/e1",
            "http://ehr.example.com/fhir/r4/Encounter/e1",
            "https://ehr.example.com:8443/fhir/r4/Encounter/e1",
        ):
            with pytest.raises(ForeignLink):
                client.local(foreign)

    await _with_client(FakeEhr(), check)


async def test_a_read_carries_a_bearer_token_fetched_once():
    ehr = FakeEhr(resources={"Encounter/e1": {"resourceType": "Encounter", "id": "e1"}})

    async def check(client: FhirClient) -> None:
        assert (await client.read("Encounter/e1", "Encounter"))["id"] == "e1"
        assert (await client.read("Encounter/e1", "Encounter"))["id"] == "e1"

    await _with_client(ehr, check)
    assert ehr.issued == ["token-1"]
    assert {request.headers["authorization"] for request in ehr.requests if "Encounter" in request.url.path} == {
        "Bearer token-1"
    }


async def test_an_expired_token_is_replaced_once_when_the_ehr_answers_401():
    ehr = FakeEhr(resources={"Practitioner/p1": {"resourceType": "Practitioner", "id": "p1"}})
    ehr.queued["/fhir/r4/Practitioner/p1"] = [httpx.Response(401)]

    async def check(client: FhirClient) -> None:
        assert (await client.read("Practitioner/p1", "Practitioner"))["id"] == "p1"

    await _with_client(ehr, check)
    assert ehr.issued == ["token-1", "token-2"]


async def test_missing_resources_and_refused_searches_are_told_apart():
    async def check(client: FhirClient) -> None:
        with pytest.raises(FhirMissing):
            await client.read("Encounter/nowhere", "Encounter")
        with pytest.raises(FhirRefused):
            await client.bundle(f"{BASE}/Nothing?x=1")

    await _with_client(FakeEhr(), check)


async def test_an_attachment_comes_back_as_bytes_or_from_a_binary_resource():
    ehr = FakeEhr(binaries={"Binary/b1": (PDF, "application/pdf")})
    binary = {"resourceType": "Binary", "contentType": "application/pdf", "data": base64.b64encode(PDF).decode()}
    wrapped = httpx.Response(200, json=binary, headers={"content-type": "application/fhir+json"})
    ehr.queued["/fhir/r4/Binary/b2"] = [wrapped]

    async def check(client: FhirClient) -> None:
        assert await client.attachment("Binary/b1", "application/pdf", max_bytes=1000) == (PDF, "application/pdf")
        assert await client.attachment("Binary/b2", "application/pdf", max_bytes=1000) == (PDF, "application/pdf")
        with pytest.raises(FhirMissing):
            await client.attachment("Binary/missing", "application/pdf", max_bytes=1000)
        with pytest.raises(TooLarge):
            await client.attachment("Binary/b1", "application/pdf", max_bytes=5)

    await _with_client(ehr, check)


def test_inline_attachment_data_is_size_checked_before_and_after_decoding():
    encoded = base64.b64encode(b"x" * 100).decode()
    assert decoded_data(encoded, 100) == b"x" * 100
    with pytest.raises(TooLarge):
        decoded_data(encoded, 50)


def test_the_next_link_is_read_from_the_bundle_links():
    bundle = {"link": [{"relation": "self", "url": "a"}, {"relation": "next", "url": "b"}]}
    assert next_link(bundle) == "b"
    assert next_link({"link": [{"relation": "self", "url": "a"}]}) is None
    assert next_link({}) is None
