import base64
import hashlib
import time
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec, rsa

from app.adapters.oidc import Endpoints, OidcProvider, ProviderConfig, ProviderIdentity, endpoints_from, pkce_challenge
from app.adapters.oidc_providers import (
    GOOGLE,
    MICROSOFT,
    PERSONAL_MICROSOFT_TENANT,
    YAHOO,
    IdentityRefused,
    ProviderUnreachable,
    UnverifiedEmail,
    tenant_allowed,
)
from app.main import app

CLIENT_ID = "client-123"
NONCE = "nonce-abc"
WORK_TENANT = "72f988bf-86f1-41af-91ab-2d7cd011db47"
RSA_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OTHER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
EC_KEY = ec.generate_private_key(ec.SECP256R1())
ENDPOINTS = Endpoints(
    "https://idp.example.com/authorize", "https://idp.example.com/token", "https://idp.example.com/keys"
)


class StaticKeys:
    def __init__(self, public_key) -> None:
        self._public_key = public_key

    def get_signing_key_from_jwt(self, token: str) -> SimpleNamespace:
        return SimpleNamespace(key=self._public_key)


def provider(spec, *, tenant: str = "", key=RSA_KEY) -> OidcProvider:
    redirect = f"https://app.test/api/auth/{spec.name}/callback"
    config = ProviderConfig(spec, CLIENT_ID, "client-secret", redirect, tenant)
    return OidcProvider(config, endpoints=ENDPOINTS, keys=StaticKeys(key.public_key()))


def id_token(*, key=RSA_KEY, algorithm: str = "RS256", **changes) -> str:
    now = int(time.time())
    claims = {"aud": CLIENT_ID, "sub": "1077", "nonce": NONCE, "iat": now, "exp": now + 600, **changes}
    return jwt.encode({name: value for name, value in claims.items() if value is not None}, key, algorithm=algorithm)


def google_token(**changes) -> str:
    base = {"iss": "https://accounts.google.com", "email": "Sam@Lakeside.example.com", "email_verified": True}
    return id_token(**{**base, **changes})


def microsoft_token(tid: str = WORK_TENANT, **changes) -> str:
    base = {"iss": f"https://login.microsoftonline.com/{tid}/v2.0", "tid": tid, "email": "Ana@Clinic.example.com"}
    return id_token(**{**base, **changes})


def yahoo_token(**changes) -> str:
    base = {"iss": "https://api.login.yahoo.com", "email": "Lee@Yahoo.example.com", "email_verified": True}
    return id_token(key=EC_KEY, algorithm="ES256", **{**base, **changes})


async def test_a_valid_google_id_token_gives_the_subject_lower_case_email_and_name():
    identity = provider(GOOGLE).identity_from(google_token(name="Sam Patel"), nonce=NONCE)
    assert identity == ProviderIdentity("google", "1077", "sam@lakeside.example.com", "Sam Patel")


async def test_the_google_issuer_without_a_scheme_is_accepted():
    assert provider(GOOGLE).identity_from(google_token(iss="accounts.google.com"), nonce=NONCE).subject == "1077"


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
async def test_a_google_id_token_is_refused_when_any_check_fails(changes):
    with pytest.raises(IdentityRefused):
        provider(GOOGLE).identity_from(google_token(**changes), nonce=NONCE)


async def test_a_personal_microsoft_account_is_trusted_without_the_domain_claim():
    token = microsoft_token(PERSONAL_MICROSOFT_TENANT, name="Ana Cruz")
    identity = provider(MICROSOFT, tenant="common").identity_from(token, nonce=NONCE)
    assert identity == ProviderIdentity("microsoft", "1077", "ana@clinic.example.com", "Ana Cruz")


async def test_a_work_microsoft_account_is_trusted_when_its_email_domain_is_verified():
    identity = provider(MICROSOFT, tenant="common").identity_from(microsoft_token(xms_edov=True), nonce=NONCE)
    assert identity.email == "ana@clinic.example.com"


@pytest.mark.parametrize("changes", [{}, {"xms_edov": False}, {"xms_edov": "1"}, {"xms_edov": True, "email": None}])
async def test_a_work_microsoft_account_without_a_verified_email_is_refused_with_its_reason(changes):
    with pytest.raises(UnverifiedEmail, match="this Microsoft account has no verified email"):
        provider(MICROSOFT, tenant="common").identity_from(microsoft_token(**changes), nonce=NONCE)


async def test_a_microsoft_token_whose_issuer_names_another_tenant_is_refused():
    token = microsoft_token(xms_edov=True, iss=f"https://login.microsoftonline.com/{PERSONAL_MICROSOFT_TENANT}/v2.0")
    with pytest.raises(IdentityRefused) as caught:
        provider(MICROSOFT, tenant="common").identity_from(token, nonce=NONCE)
    assert not isinstance(caught.value, UnverifiedEmail)


async def test_a_microsoft_token_without_a_tenant_is_refused():
    with pytest.raises(IdentityRefused):
        provider(MICROSOFT, tenant="common").identity_from(microsoft_token(tid=None, xms_edov=True), nonce=NONCE)


@pytest.mark.parametrize(
    ("tenant", "tid", "allowed"),
    [
        ("common", WORK_TENANT, True),
        ("common", PERSONAL_MICROSOFT_TENANT, True),
        ("organizations", WORK_TENANT, True),
        ("organizations", PERSONAL_MICROSOFT_TENANT, False),
        ("consumers", PERSONAL_MICROSOFT_TENANT, True),
        ("consumers", WORK_TENANT, False),
        (WORK_TENANT, WORK_TENANT, True),
        (WORK_TENANT, PERSONAL_MICROSOFT_TENANT, False),
    ],
)
async def test_the_microsoft_tenant_setting_limits_which_accounts_sign_in(tenant, tid, allowed):
    assert tenant_allowed(tenant, tid) is allowed


async def test_a_single_tenant_setting_refuses_a_token_from_another_tenant():
    token = microsoft_token(PERSONAL_MICROSOFT_TENANT)
    with pytest.raises(IdentityRefused):
        provider(MICROSOFT, tenant=WORK_TENANT).identity_from(token, nonce=NONCE)


async def test_a_valid_yahoo_id_token_signed_with_es256_is_accepted():
    identity = provider(YAHOO, key=EC_KEY).identity_from(yahoo_token(given_name="Lee", family_name="Wong"), nonce=NONCE)
    assert identity == ProviderIdentity("yahoo", "1077", "lee@yahoo.example.com", "Lee Wong")


async def test_a_yahoo_token_without_the_verified_flag_is_accepted():
    assert provider(YAHOO, key=EC_KEY).identity_from(yahoo_token(email_verified=None), nonce=NONCE).subject == "1077"


@pytest.mark.parametrize("changes", [{"email_verified": False}, {"email": None}])
async def test_a_yahoo_token_without_a_verified_email_is_refused(changes):
    with pytest.raises(UnverifiedEmail, match="this Yahoo account has no verified email"):
        provider(YAHOO, key=EC_KEY).identity_from(yahoo_token(**changes), nonce=NONCE)


async def test_a_yahoo_token_from_another_issuer_is_refused():
    with pytest.raises(IdentityRefused):
        provider(YAHOO, key=EC_KEY).identity_from(yahoo_token(iss="https://login.example.com"), nonce=NONCE)


async def test_the_pkce_challenge_matches_the_rfc_7636_example():
    assert (
        pkce_challenge("dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk") == "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"
    )


@pytest.mark.parametrize(
    "document",
    [
        {"authorization_endpoint": "https://a", "token_endpoint": "https://t"},
        {"authorization_endpoint": "http://a", "token_endpoint": "https://t", "jwks_uri": "https://k"},
        ["not", "a", "document"],
    ],
)
async def test_a_discovery_document_without_secure_endpoints_is_refused(document):
    with pytest.raises(ProviderUnreachable):
        endpoints_from(document)


@pytest.mark.parametrize("spec", [GOOGLE, MICROSOFT, YAHOO])
async def test_every_provider_starts_with_s256_and_keeps_its_state_in_a_lax_cookie(harness, spec):
    app.state.identity_providers[spec.name] = provider(spec, tenant="common")
    start = await harness.client.get(f"/api/auth/{spec.name}/start")
    assert start.status_code == 302
    location = urlsplit(start.headers["location"])
    query = {name: values[0] for name, values in parse_qs(location.query).items()}
    assert f"{location.scheme}://{location.netloc}{location.path}" == ENDPOINTS.authorization
    redirect = f"https://app.test/api/auth/{spec.name}/callback"
    assert (query["client_id"], query["redirect_uri"], query["response_type"]) == (CLIENT_ID, redirect, "code")
    assert (query["scope"], query["code_challenge_method"]) == ("openid email profile", "S256")
    cookie = start.headers["set-cookie"].lower()
    assert all(part in cookie for part in ("httponly", "secure", "samesite=lax", f"path=/api/auth/{spec.name}"))
    path = f"/api/auth/{spec.name}"
    started = jwt.decode(
        harness.client.cookies.get("bodha_oidc", domain="app.test", path=path), options={"verify_signature": False}
    )
    assert (started["sub"], started["nonce"], started["idp"]) == (query["state"], query["nonce"], spec.name)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(started["pkce"].encode()).digest()).rstrip(b"=").decode()
    assert query["code_challenge"] == challenge
