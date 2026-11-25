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

from app.core.config import Settings
from app.core.errors import Unauthorized, Unavailable

AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
CERTS_URL = "https://www.googleapis.com/oauth2/v3/certs"
CALLBACK_PATH = "/api/auth/google/callback"
ISSUERS = ("accounts.google.com", "https://accounts.google.com")
REQUIRED_CLAIMS = ["iss", "aud", "exp", "iat", "sub", "email", "nonce"]
SCOPES = "openid email"
TIMEOUT_SECONDS = 15
CLOCK_LEEWAY_SECONDS = 60


class GoogleRefused(Unauthorized):
    pass


class GoogleUnreachable(Unavailable):
    pass


@dataclass(frozen=True)
class GoogleIdentity:
    sub: str
    email: str


class SigningKeys(Protocol):
    def get_signing_key_from_jwt(self, token: str) -> Any: ...


class GoogleSignIn(Protocol):
    @property
    def enabled(self) -> bool: ...

    def authorization_url(self, *, state: str, nonce: str, verifier: str) -> str: ...

    async def identity(self, code: str, *, verifier: str, nonce: str) -> GoogleIdentity: ...


class GoogleOidc:
    def __init__(
        self, *, client_id: str | None, client_secret: str | None, redirect_uri: str, keys: SigningKeys
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri
        self._keys = keys

    @property
    def enabled(self) -> bool:
        return bool(self._client_id and self._client_secret)

    def authorization_url(self, *, state: str, nonce: str, verifier: str) -> str:
        query = {
            "client_id": self._client_id or "",
            "redirect_uri": self._redirect_uri,
            "response_type": "code",
            "scope": SCOPES,
            "state": state,
            "nonce": nonce,
            "code_challenge": pkce_challenge(verifier),
            "code_challenge_method": "S256",
            "prompt": "select_account",
        }
        return f"{AUTHORIZE_URL}?{urlencode(query)}"

    async def identity(self, code: str, *, verifier: str, nonce: str) -> GoogleIdentity:
        if not self.enabled:
            raise GoogleRefused("Google sign-in is not set up")
        id_token = await self._exchange(code, verifier)
        return await asyncio.to_thread(self.identity_from, id_token, nonce=nonce)

    def identity_from(self, id_token: str, *, nonce: str) -> GoogleIdentity:
        try:
            key = self._keys.get_signing_key_from_jwt(id_token)
            claims = jwt.decode(
                id_token,
                key.key,
                algorithms=["RS256"],
                audience=self._client_id,
                issuer=ISSUERS,
                leeway=CLOCK_LEEWAY_SECONDS,
                options={"require": REQUIRED_CLAIMS},
            )
        except jwt.PyJWKClientConnectionError as error:
            raise GoogleUnreachable("Google's signing keys could not be fetched") from error
        except jwt.PyJWTError as error:
            raise GoogleRefused("the Google identity is not valid") from error
        if not hmac.compare_digest(str(claims["nonce"]), nonce):
            raise GoogleRefused("the Google identity belongs to another sign-in")
        if claims.get("email_verified") is not True:
            raise GoogleRefused("Google has not verified this email")
        return GoogleIdentity(sub=str(claims["sub"]), email=str(claims["email"]).strip().lower())

    async def _exchange(self, code: str, verifier: str) -> str:
        form = {
            "code": code,
            "client_id": self._client_id or "",
            "client_secret": self._client_secret or "",
            "redirect_uri": self._redirect_uri,
            "grant_type": "authorization_code",
            "code_verifier": verifier,
        }
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
                response = await client.post(TOKEN_URL, data=form)
            payload = response.json() if response.status_code < 400 else {}
        except (httpx.HTTPError, ValueError) as error:
            raise GoogleUnreachable("Google could not be reached") from error
        id_token = payload.get("id_token") if isinstance(payload, dict) else None
        if not isinstance(id_token, str):
            raise GoogleRefused("Google did not accept the sign-in")
        return id_token


def pkce_challenge(verifier: str) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()


def build_google_sign_in(settings: Settings) -> GoogleOidc:
    return GoogleOidc(
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        redirect_uri=settings.app_url.rstrip("/") + CALLBACK_PATH,
        keys=jwt.PyJWKClient(CERTS_URL, cache_keys=True, timeout=TIMEOUT_SECONDS),
    )
