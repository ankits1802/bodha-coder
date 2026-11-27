from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from app.core.errors import Unauthorized, Unavailable

SCOPES = "openid email profile"
NAME_LENGTH = 120
GOOGLE_ISSUERS = ("accounts.google.com", "https://accounts.google.com")
MICROSOFT_ISSUER = "https://login.microsoftonline.com/{tenant}/v2.0"
PERSONAL_MICROSOFT_TENANT = "9188040d-6c67-4c5b-b112-36a304b66dad"
ANY_MICROSOFT_TENANT = "common"
ORGANIZATION_TENANTS = "organizations"
PERSONAL_TENANTS = "consumers"
YAHOO_ISSUER = "https://api.login.yahoo.com"
BASE_CLAIMS = ("iss", "aud", "exp", "iat", "sub", "nonce")

Claims = Mapping[str, Any]


class IdentityRefused(Unauthorized):
    pass


class UnverifiedEmail(IdentityRefused):
    pass


class ProviderUnreachable(Unavailable):
    pass


@dataclass(frozen=True)
class ProviderSpec:
    name: str
    label: str
    discovery_url: str
    algorithms: tuple[str, ...]
    required_claims: tuple[str, ...]
    issuers: Callable[[Claims, str], tuple[str, ...]]
    trusted_email: Callable[[Claims, str], str]
    client_id_setting: str
    client_secret_setting: str
    tenant_setting: str | None = None
    prompt: str | None = None


def display_name(claims: Claims) -> str:
    full = str(claims.get("name") or "").strip()
    if not full:
        parts = (str(claims.get("given_name") or "").strip(), str(claims.get("family_name") or "").strip())
        full = " ".join(part for part in parts if part)
    return full[:NAME_LENGTH]


def _email(claims: Claims) -> str:
    return str(claims.get("email") or "").strip().lower()


def _google_issuers(claims: Claims, tenant: str) -> tuple[str, ...]:
    return GOOGLE_ISSUERS


def _google_email(claims: Claims, tenant: str) -> str:
    if claims.get("email_verified") is not True or not _email(claims):
        raise UnverifiedEmail("Google has not verified this email")
    return _email(claims)


def tenant_allowed(tenant: str, tid: str) -> bool:
    if tenant == ANY_MICROSOFT_TENANT:
        return True
    if tenant == PERSONAL_TENANTS:
        return tid == PERSONAL_MICROSOFT_TENANT
    if tenant == ORGANIZATION_TENANTS:
        return tid != PERSONAL_MICROSOFT_TENANT
    return tid == tenant


def _microsoft_issuers(claims: Claims, tenant: str) -> tuple[str, ...]:
    tid = str(claims.get("tid") or "")
    if not tid or not tenant_allowed(tenant, tid):
        return ()
    return (MICROSOFT_ISSUER.format(tenant=tid),)


def _microsoft_email(claims: Claims, tenant: str) -> str:
    verified = claims.get("xms_edov") is True or claims.get("tid") == PERSONAL_MICROSOFT_TENANT
    if not verified or not _email(claims):
        raise UnverifiedEmail("this Microsoft account has no verified email")
    return _email(claims)


def _yahoo_issuers(claims: Claims, tenant: str) -> tuple[str, ...]:
    return (YAHOO_ISSUER,)


def _yahoo_email(claims: Claims, tenant: str) -> str:
    if not _email(claims) or ("email_verified" in claims and claims["email_verified"] is not True):
        raise UnverifiedEmail("this Yahoo account has no verified email")
    return _email(claims)


GOOGLE = ProviderSpec(
    name="google",
    label="Google",
    discovery_url="https://accounts.google.com/.well-known/openid-configuration",
    algorithms=("RS256",),
    required_claims=(*BASE_CLAIMS, "email"),
    issuers=_google_issuers,
    trusted_email=_google_email,
    client_id_setting="google_client_id",
    client_secret_setting="google_client_secret",
    prompt="select_account",
)
MICROSOFT = ProviderSpec(
    name="microsoft",
    label="Microsoft",
    discovery_url="https://login.microsoftonline.com/{tenant}/v2.0/.well-known/openid-configuration",
    algorithms=("RS256",),
    required_claims=(*BASE_CLAIMS, "tid"),
    issuers=_microsoft_issuers,
    trusted_email=_microsoft_email,
    client_id_setting="microsoft_client_id",
    client_secret_setting="microsoft_client_secret",
    tenant_setting="microsoft_tenant",
    prompt="select_account",
)
YAHOO = ProviderSpec(
    name="yahoo",
    label="Yahoo",
    discovery_url="https://api.login.yahoo.com/.well-known/openid-configuration",
    algorithms=("ES256", "RS256"),
    required_claims=BASE_CLAIMS,
    issuers=_yahoo_issuers,
    trusted_email=_yahoo_email,
    client_id_setting="yahoo_client_id",
    client_secret_setting="yahoo_client_secret",
)
PROVIDERS: dict[str, ProviderSpec] = {spec.name: spec for spec in (GOOGLE, MICROSOFT, YAHOO)}
PROVIDER_NAMES = tuple(PROVIDERS)


def provider_label(name: str) -> str:
    return PROVIDERS[name].label
