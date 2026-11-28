from __future__ import annotations

import base64
import hashlib
import json
import secrets
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from jwt.algorithms import ECAlgorithm, RSAAlgorithm

from app.adapters.guarded_http import GuardedHttp, OutboundError, require_https

__all__ = [
    "ASSERTION_SECONDS",
    "ASSERTION_TYPE",
    "SIGNING_ALGORITHMS",
    "SMART_REASONS",
    "AccessToken",
    "BadAnswer",
    "KeyPair",
    "NoSmartConfiguration",
    "ServerFailed",
    "SmartClient",
    "SmartConfiguration",
    "TokenRefused",
    "client_assertion",
    "discover",
    "fetch_token",
    "json_object",
    "jwk_thumbprint",
    "new_key_pair",
    "read_smart_configuration",
    "read_token",
]

SIGNING_ALGORITHMS = ("RS384", "ES384")
RSA_BITS = 3072
ASSERTION_TYPE = "urn:ietf:params:oauth:client-assertion-type:jwt-bearer"
ASSERTION_SECONDS = 240
DEFAULT_TOKEN_SECONDS = 300
JSON_LIMIT = 1_000_000
CONFIGURATION_PATH = "/.well-known/smart-configuration"
THUMBPRINT_MEMBERS = {"RSA": ("e", "kty", "n"), "EC": ("crv", "kty", "x", "y")}
OAUTH_ERROR_LENGTH = 40


class NoSmartConfiguration(OutboundError):
    reason = "no_configuration"


class TokenRefused(OutboundError):
    reason = "token_refused"


class ServerFailed(OutboundError):
    reason = "server_error"


class BadAnswer(OutboundError):
    reason = "bad_response"


SMART_REASONS = tuple(kind.reason for kind in (NoSmartConfiguration, TokenRefused, ServerFailed, BadAnswer))


@dataclass(frozen=True)
class KeyPair:
    kid: str
    algorithm: str
    private_pem: str
    public_jwk: dict[str, Any]


@dataclass(frozen=True)
class SmartConfiguration:
    token_endpoint: str
    auth_methods: tuple[str, ...]
    signing_algorithms: tuple[str, ...]
    grant_types: tuple[str, ...]
    scopes: tuple[str, ...]


@dataclass(frozen=True)
class SmartClient:
    client_id: str
    token_endpoint: str
    scopes: str
    kid: str
    algorithm: str
    private_pem: str


@dataclass(frozen=True)
class AccessToken:
    value: str
    expires_in: int
    scope: str


def new_key_pair(algorithm: str) -> KeyPair:
    if algorithm == "RS384":
        rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=RSA_BITS)
        return _pair(algorithm, rsa_key, RSAAlgorithm.to_jwk(rsa_key.public_key(), as_dict=True))
    if algorithm == "ES384":
        ec_key = ec.generate_private_key(ec.SECP384R1())
        return _pair(algorithm, ec_key, ECAlgorithm.to_jwk(ec_key.public_key(), as_dict=True))
    raise ValueError(f"{algorithm} is not a signing algorithm Bodha offers")


def jwk_thumbprint(jwk: dict[str, Any]) -> str:
    members = THUMBPRINT_MEMBERS[str(jwk["kty"])]
    canonical = json.dumps({name: jwk[name] for name in members}, separators=(",", ":"), sort_keys=True)
    return base64.urlsafe_b64encode(hashlib.sha256(canonical.encode()).digest()).decode().rstrip("=")


def client_assertion(client: SmartClient, *, now: datetime, jti: str) -> str:
    issued = int(now.timestamp())
    claims = {
        "iss": client.client_id,
        "sub": client.client_id,
        "aud": client.token_endpoint,
        "jti": jti,
        "iat": issued,
        "exp": issued + ASSERTION_SECONDS,
    }
    key = serialization.load_pem_private_key(client.private_pem.encode(), password=None)
    return jwt.encode(claims, key, algorithm=client.algorithm, headers={"kid": client.kid, "typ": "JWT"})


async def discover(http: GuardedHttp, base_url: str) -> SmartConfiguration:
    answer = await http.get(
        f"{base_url}{CONFIGURATION_PATH}", headers={"Accept": "application/json"}, max_bytes=JSON_LIMIT
    )
    if answer.status != 200:
        raise NoSmartConfiguration(f"the smart configuration address answered {answer.status}")
    return read_smart_configuration(answer.body)


async def fetch_token(http: GuardedHttp, client: SmartClient, *, now: datetime) -> AccessToken:
    form = {
        "grant_type": "client_credentials",
        "scope": client.scopes,
        "client_assertion_type": ASSERTION_TYPE,
        "client_assertion": client_assertion(client, now=now, jti=secrets.token_urlsafe(24)),
    }
    answer = await http.post_form(
        client.token_endpoint, form, headers={"Accept": "application/json"}, max_bytes=JSON_LIMIT
    )
    if 400 <= answer.status < 500:
        raise TokenRefused(f"the token endpoint answered {answer.status}{_oauth_error(answer.body)}")
    if answer.status != 200:
        raise ServerFailed(f"the token endpoint answered {answer.status}")
    return read_token(answer.body)


def read_smart_configuration(body: bytes) -> SmartConfiguration:
    data = json_object(body)
    endpoint = data.get("token_endpoint")
    if not isinstance(endpoint, str) or not endpoint:
        raise NoSmartConfiguration("the smart configuration names no token endpoint")
    try:
        require_https(endpoint)
    except OutboundError as error:
        raise NoSmartConfiguration("the token endpoint is not an https address") from error
    return SmartConfiguration(
        token_endpoint=endpoint,
        auth_methods=_strings(data, "token_endpoint_auth_methods_supported"),
        signing_algorithms=_strings(data, "token_endpoint_auth_signing_alg_values_supported"),
        grant_types=_strings(data, "grant_types_supported"),
        scopes=_strings(data, "scopes_supported"),
    )


def read_token(body: bytes) -> AccessToken:
    data = json_object(body)
    value, kind = data.get("access_token"), data.get("token_type")
    if not isinstance(value, str) or not value:
        raise BadAnswer("the token answer has no access token")
    if not isinstance(kind, str) or kind.lower() != "bearer":
        raise BadAnswer("the token answer is not a bearer token")
    expires = data.get("expires_in", DEFAULT_TOKEN_SECONDS)
    if not isinstance(expires, int) or isinstance(expires, bool) or expires <= 0:
        raise BadAnswer("the token answer has no usable lifetime")
    scope = data.get("scope", "")
    return AccessToken(value, expires, scope if isinstance(scope, str) else "")


def json_object(body: bytes) -> dict[str, Any]:
    try:
        data = json.loads(body)
    except (UnicodeDecodeError, ValueError) as error:
        raise BadAnswer("the server did not answer with JSON") from error
    if not isinstance(data, dict):
        raise BadAnswer("the server did not answer with a JSON object")
    return data


def _pair(algorithm: str, key: rsa.RSAPrivateKey | ec.EllipticCurvePrivateKey, jwk: Any) -> KeyPair:
    public = dict(jwk)
    kid = jwk_thumbprint(public)
    public.update(kid=kid, alg=algorithm, use="sig", key_ops=["verify"])
    pem = key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    ).decode()
    return KeyPair(kid, algorithm, pem, public)


def _strings(data: dict[str, Any], name: str) -> tuple[str, ...]:
    found = data.get(name)
    if not isinstance(found, list):
        return ()
    return tuple(item for item in found if isinstance(item, str))


def _oauth_error(body: bytes) -> str:
    try:
        code = json.loads(body).get("error")
    except (UnicodeDecodeError, ValueError, AttributeError):
        return ""
    if not isinstance(code, str) or not code.replace("_", "").isalnum():
        return ""
    return f" {code[:OAUTH_ERROR_LENGTH]}"
