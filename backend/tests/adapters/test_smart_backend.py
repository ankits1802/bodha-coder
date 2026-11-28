from __future__ import annotations

import json
from datetime import UTC, datetime
from urllib.parse import parse_qs

import httpx
import jwt
import pytest

from app.adapters.fhir_client import FHIR_REASONS
from app.adapters.guarded_http import OUTBOUND_REASONS, OutboundHttp
from app.adapters.smart_backend import (
    ASSERTION_TYPE,
    SMART_REASONS,
    BadAnswer,
    NoSmartConfiguration,
    SmartClient,
    TokenRefused,
    client_assertion,
    fetch_token,
    jwk_thumbprint,
    new_key_pair,
    read_smart_configuration,
    read_token,
)
from app.models import PULL_REASONS
from tests.ehr_fakes import FAST, TOKEN_URL, Sleeps, public_resolver

RFC_7638_KEY = {
    "kty": "RSA",
    "n": "0vx7agoebGcQSuuPiLJXZptN9nndrQmbXEps2aiAFbWhM78LhWx4cbbfAAtVT86zwu1RK7aPFFxuhDR1L6tSoc_BJECPebWKRXjBZCiFV4n3o"
    "knjhMstn64tZ_2W-5JsGY4Hc5n9yBXArwl93lqt7_RN5w6Cf0h4QyQ5v-65YGjQR0_FDW2QvzqY368QQMicAtaSqzs8KJZgnYb9c7d0zgdAZHzu6"
    "qMQvRL5hajrn1n91CbOpbISD08qNLyrdkt-bFTWhAI4vMQFh6WeZu0fM4lFd2NcRwr3XPksINHaQ-G_xBniIqbw0Ls1jF44-csFCur-kEgU8awapJ"
    "zKnqDKgw",
    "e": "AQAB",
    "alg": "RS256",
    "kid": "2011-04-29",
}
NOW = datetime(2026, 11, 27, 15, 0, tzinfo=UTC)
PRIVATE_MEMBERS = {"d", "p", "q", "dp", "dq", "qi"}


def _client(algorithm: str) -> tuple[SmartClient, dict]:
    pair = new_key_pair(algorithm)
    client = SmartClient(
        "bodha-client", TOKEN_URL, "system/DocumentReference.read", pair.kid, algorithm, pair.private_pem
    )
    return client, pair.public_jwk


def test_the_key_id_is_the_rfc_7638_thumbprint():
    assert jwk_thumbprint(RFC_7638_KEY) == "NzbLsXh8uDCcd-6MNwXF4W_7noWXFZAfHkxZsRGC9Xs"


@pytest.mark.parametrize(("algorithm", "kty"), [("RS384", "RSA"), ("ES384", "EC")])
def test_a_new_key_publishes_only_public_members(algorithm, kty):
    pair = new_key_pair(algorithm)
    assert not PRIVATE_MEMBERS & set(pair.public_jwk)
    assert (pair.public_jwk["kty"], pair.public_jwk["alg"], pair.public_jwk["use"]) == (kty, algorithm, "sig")
    assert pair.public_jwk["kid"] == pair.kid == jwk_thumbprint(pair.public_jwk)
    assert pair.private_pem.startswith("-----BEGIN PRIVATE KEY-----")


def test_only_rs384_and_es384_keys_are_made():
    with pytest.raises(ValueError):
        new_key_pair("RS256")


@pytest.mark.parametrize("algorithm", ["RS384", "ES384"])
def test_the_client_assertion_carries_the_backend_services_claims(algorithm):
    client, public = _client(algorithm)

    token = client_assertion(client, now=NOW, jti="one-time")

    header = jwt.get_unverified_header(token)
    assert (header["alg"], header["kid"], header["typ"]) == (algorithm, client.kid, "JWT")
    assert "jku" not in header
    claims = jwt.decode(
        token, jwt.PyJWK(public).key, algorithms=[algorithm], audience=TOKEN_URL, options={"verify_exp": False}
    )
    assert (claims["iss"], claims["sub"], claims["aud"], claims["jti"]) == (
        "bodha-client",
        "bodha-client",
        TOKEN_URL,
        "one-time",
    )
    assert claims["exp"] - int(NOW.timestamp()) == 240


def test_the_smart_configuration_needs_an_https_token_endpoint():
    found = read_smart_configuration(json.dumps({"token_endpoint": TOKEN_URL, "grant_types_supported": ["x"]}).encode())
    assert (found.token_endpoint, found.grant_types, found.auth_methods) == (TOKEN_URL, ("x",), ())
    for body in ({"token_endpoint": "http://auth.example.com/token"}, {}, ["not", "an", "object"]):
        with pytest.raises((NoSmartConfiguration, BadAnswer)):
            read_smart_configuration(json.dumps(body).encode())


def test_a_token_answer_must_be_a_bearer_token():
    assert read_token(b'{"access_token": "a", "token_type": "Bearer"}').expires_in == 300
    for body in (b'{"token_type": "bearer"}', b'{"access_token": "a", "token_type": "mac"}', b"not json"):
        with pytest.raises(BadAnswer):
            read_token(body)


async def test_the_token_request_is_a_signed_client_credentials_grant():
    client, public = _client("RS384")
    sent: list[dict[str, list[str]]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(parse_qs(request.content.decode()))
        return httpx.Response(200, json={"access_token": "t", "token_type": "bearer", "expires_in": 120, "scope": "s"})

    outbound = OutboundHttp(httpx.MockTransport(handler), public_resolver, Sleeps(), FAST)
    async with outbound.connect() as http:
        token = await fetch_token(http, client, now=datetime.now(UTC))

    assert (token.value, token.expires_in, token.scope) == ("t", 120, "s")
    [form] = sent
    assert form["grant_type"] == ["client_credentials"]
    assert form["client_assertion_type"] == [ASSERTION_TYPE]
    assert form["scope"] == ["system/DocumentReference.read"]
    jwt.decode(form["client_assertion"][0], jwt.PyJWK(public).key, algorithms=["RS384"], audience=TOKEN_URL)


async def test_a_refused_token_names_the_status_and_oauth_error_only():
    client, _ = _client("ES384")
    answer = httpx.Response(401, json={"error": "invalid_client", "error_description": "Patient REYES not allowed"})
    outbound = OutboundHttp(httpx.MockTransport(lambda request: answer), public_resolver, Sleeps(), FAST)
    async with outbound.connect() as http:
        with pytest.raises(TokenRefused) as refused:
            await fetch_token(http, client, now=NOW)
    assert refused.value.message == "the token endpoint answered 401 invalid_client"


def test_every_reason_an_adapter_gives_is_a_reason_a_pull_run_can_record():
    assert set(OUTBOUND_REASONS) | set(SMART_REASONS) | set(FHIR_REASONS) <= set(PULL_REASONS)
