from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import urlencode

import httpx
import jwt
from pydantic import SecretStr

from app.adapters.oidc_providers import (
    PROVIDERS,
    SCOPES,
    IdentityRefused,
    ProviderSpec,
    ProviderUnreachable,
    display_name,
)
from app.core.config import Settings

CALLBACK_PATH = "/api/auth/{provider}/callback"
TIMEOUT_SECONDS = 15
CLOCK_LEEWAY_SECONDS = 60
SECURE_SCHEME = "https://"


@dataclass(frozen=True)
class ProviderIdentity:
    provider: str
    subject: str
    email: str
    name: str


@dataclass(frozen=True)
class Endpoints:
    authorization: str
    token: str
    jwks: str


@dataclass(frozen=True)
class ProviderConfig:
    spec: ProviderSpec
    client_id: str | None
    client_secret: str | None
    redirect_uri: str
    tenant: str = ""


class SigningKeys(Protocol):
    def get_signing_key_from_jwt(self, token: str) -> Any: ...


class IdentityProvider(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def label(self) -> str: ...

    @property
    def enabled(self) -> bool: ...

    async def authorization_url(self, *, state: str, nonce: str, verifier: str) -> str: ...

    async def identity(self, code: str, *, verifier: str, nonce: str) -> ProviderIdentity: ...


class OidcProvider:
    def __init__(
        self, config: ProviderConfig, *, endpoints: Endpoints | None = None, keys: SigningKeys | None = None
    ) -> None:
        self._config = config
        self._endpoints = endpoints
        self._keys = keys

    @property
    def name(self) -> str:
        return self._config.spec.name

    @property
    def label(self) -> str:
        return self._config.spec.label

    @property
    def enabled(self) -> bool:
        return bool(self._config.client_id and self._config.client_secret)

    async def authorization_url(self, *, state: str, nonce: str, verifier: str) -> str:
        endpoints = await self._discovered()
        query = {
            "client_id": self._config.client_id or "",
            "redirect_uri": self._config.redirect_uri,
            "response_type": "code",
            "scope": SCOPES,
            "state": state,
            "nonce": nonce,
            "code_challenge": pkce_challenge(verifier),
            "code_challenge_method": "S256",
        }
        if self._config.spec.prompt:
            query["prompt"] = self._config.spec.prompt
        return f"{endpoints.authorization}?{urlencode(query)}"

    async def identity(self, code: str, *, verifier: str, nonce: str) -> ProviderIdentity:
        if not self.enabled:
            raise IdentityRefused(f"{self.label} sign-in is not set up")
        endpoints = await self._discovered()
        id_token = await self._exchange(endpoints.token, code, verifier)
        if self._keys is None:
            self._keys = jwt.PyJWKClient(endpoints.jwks, cache_keys=True, timeout=TIMEOUT_SECONDS)
        return await asyncio.to_thread(self.identity_from, id_token, nonce=nonce)

    def identity_from(self, id_token: str, *, nonce: str) -> ProviderIdentity:
        spec, tenant = self._config.spec, self._config.tenant
        claims = self._verified_claims(id_token)
        if str(claims["iss"]) not in spec.issuers(claims, tenant):
            raise IdentityRefused(f"the identity was not issued by {spec.label}")
        if not hmac.compare_digest(str(claims["nonce"]), nonce):
            raise IdentityRefused(f"the {spec.label} identity belongs to another sign-in")
        email = spec.trusted_email(claims, tenant)
        return ProviderIdentity(spec.name, str(claims["sub"]), email, display_name(claims))

    def _verified_claims(self, id_token: str) -> dict[str, Any]:
        if self._keys is None:
            raise ProviderUnreachable(f"{self.label}'s signing keys are not loaded")
        try:
            key = self._keys.get_signing_key_from_jwt(id_token)
            return jwt.decode(
                id_token,
                key.key,
                algorithms=list(self._config.spec.algorithms),
                audience=self._config.client_id,
                leeway=CLOCK_LEEWAY_SECONDS,
                options={"require": list(self._config.spec.required_claims)},
            )
        except jwt.PyJWKClientConnectionError as error:
            raise ProviderUnreachable(f"{self.label}'s signing keys could not be fetched") from error
        except jwt.PyJWTError as error:
            raise IdentityRefused(f"the {self.label} identity is not valid") from error

    async def _discovered(self) -> Endpoints:
        if self._endpoints is None:
            url = self._config.spec.discovery_url.format(tenant=self._config.tenant)
            self._endpoints = endpoints_from(await self._fetch_json(url))
        return self._endpoints

    async def _fetch_json(self, url: str) -> Any:
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
                response = await client.get(url)
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise ProviderUnreachable(f"{self.label} could not be reached") from error

    async def _exchange(self, token_url: str, code: str, verifier: str) -> str:
        form = {
            "code": code,
            "client_id": self._config.client_id or "",
            "client_secret": self._config.client_secret or "",
            "redirect_uri": self._config.redirect_uri,
            "grant_type": "authorization_code",
            "code_verifier": verifier,
        }
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
                response = await client.post(token_url, data=form)
            payload = response.json() if response.status_code < 400 else {}
        except (httpx.HTTPError, ValueError) as error:
            raise ProviderUnreachable(f"{self.label} could not be reached") from error
        id_token = payload.get("id_token") if isinstance(payload, dict) else None
        if not isinstance(id_token, str):
            raise IdentityRefused(f"{self.label} did not accept the sign-in")
        return id_token


def endpoints_from(document: Any) -> Endpoints:
    fields = ("authorization_endpoint", "token_endpoint", "jwks_uri")
    values = [document.get(field) if isinstance(document, dict) else None for field in fields]
    if not all(isinstance(value, str) and value.startswith(SECURE_SCHEME) for value in values):
        raise ProviderUnreachable("the sign-in provider's discovery document is not usable")
    return Endpoints(*values)


def pkce_challenge(verifier: str) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()


def provider_config(settings: Settings, spec: ProviderSpec) -> ProviderConfig:
    secret: SecretStr | None = getattr(settings, spec.client_secret_setting)
    return ProviderConfig(
        spec=spec,
        client_id=getattr(settings, spec.client_id_setting),
        client_secret=secret.get_secret_value() if secret else None,
        redirect_uri=settings.app_url.rstrip("/") + CALLBACK_PATH.format(provider=spec.name),
        tenant=getattr(settings, spec.tenant_setting) if spec.tenant_setting else "",
    )


def build_identity_providers(settings: Settings) -> dict[str, IdentityProvider]:
    return {name: OidcProvider(provider_config(settings, spec)) for name, spec in PROVIDERS.items()}
