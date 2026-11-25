import base64
import hashlib
import time
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from app.adapters.google_oidc import GoogleOidc, GoogleRefused, pkce_challenge
from app.main import app

CLIENT_ID = "client-123.apps.googleusercontent.com"
REDIRECT_URI = "https://app.test/api/auth/google/callback"
NONCE = "nonce-abc"
GOOGLE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OTHER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


class StaticKeys:
    def __init__(self, public_key) -> None:
        self._public_key = public_key

    def get_signing_key_from_jwt(self, token: str) -> SimpleNamespace:
        return SimpleNamespace(key=self._public_key)


def google() -> GoogleOidc:
    return GoogleOidc(
        client_id=CLIENT_ID,
        client_secret="client-secret",
        redirect_uri=REDIRECT_URI,
        keys=StaticKeys(GOOGLE_KEY.public_key()),
    )


def id_token(*, key=GOOGLE_KEY, **changes) -> str:
    now = int(time.time())
    claims = {
        "iss": "https://accounts.google.com",
        "aud": CLIENT_ID,
        "sub": "1077",
        "email": "Sam@Lakeside.example.com",
        "email_verified": True,
        "nonce": NONCE,
        "iat": now,
        "exp": now + 600,
        **changes,
    }
    return jwt.encode({name: value for name, value in claims.items() if value is not None}, key, algorithm="RS256")


async def test_a_valid_id_token_gives_the_subject_and_the_lower_case_email():
    identity = google().identity_from(id_token(), nonce=NONCE)
    assert (identity.sub, identity.email) == ("1077", "sam@lakeside.example.com")


async def test_the_issuer_without_a_scheme_is_accepted():
    assert google().identity_from(id_token(iss="accounts.google.com"), nonce=NONCE).sub == "1077"


@pytest.mark.parametrize(
    "changes",
    [
        {"aud": "another-client"},
        {"iss": "https://accounts.example.com"},
        {"exp": int(time.time()) - 3600},
        {"email_verified": False},
        {"email_verified": None},
        {"nonce": "another-nonce"},
        {"nonce": None},
        {"key": OTHER_KEY},
    ],
)
async def test_an_id_token_is_refused_when_any_check_fails(changes):
    with pytest.raises(GoogleRefused):
        google().identity_from(id_token(**changes), nonce=NONCE)


async def test_the_pkce_challenge_matches_the_rfc_7636_example():
    assert (
        pkce_challenge("dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk") == "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"
    )


async def test_google_start_redirects_with_s256_and_keeps_the_state_in_a_lax_cookie(harness):
    app.state.google = google()
    start = await harness.client.get("/api/auth/google/start")
    assert start.status_code == 302
    location = urlsplit(start.headers["location"])
    query = {name: values[0] for name, values in parse_qs(location.query).items()}
    assert f"{location.scheme}://{location.netloc}{location.path}" == "https://accounts.google.com/o/oauth2/v2/auth"
    assert (query["client_id"], query["redirect_uri"], query["response_type"]) == (CLIENT_ID, REDIRECT_URI, "code")
    assert (query["scope"], query["code_challenge_method"]) == ("openid email", "S256")
    cookie = start.headers["set-cookie"].lower()
    assert all(part in cookie for part in ("httponly", "secure", "samesite=lax", "path=/api/auth/google"))
    started = jwt.decode(
        harness.client.cookies.get("bodha_google", domain="app.test", path="/api/auth/google"),
        options={"verify_signature": False},
    )
    assert (started["sub"], started["nonce"]) == (query["state"], query["nonce"])
    challenge = base64.urlsafe_b64encode(hashlib.sha256(started["pkce"].encode()).digest()).rstrip(b"=").decode()
    assert query["code_challenge"] == challenge
