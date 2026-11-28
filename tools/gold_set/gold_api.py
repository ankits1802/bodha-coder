from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

import httpx
import pyotp

__all__ = [
    "DEFAULT_BASE_URL",
    "ENV_EMAIL",
    "ENV_PASSWORD",
    "ENV_PRACTICE",
    "ENV_TOTP",
    "ApiError",
    "BodhaApi",
    "Credentials",
    "SetupError",
]

DEFAULT_BASE_URL = "https://www.bodhaai.co"
ENV_EMAIL = "BODHA_EVAL_EMAIL"
ENV_PASSWORD = "BODHA_EVAL_PASSWORD"
ENV_TOTP = "BODHA_EVAL_TOTP_SECRET"
ENV_PRACTICE = "BODHA_EVAL_PRACTICE_ID"
REQUEST_SECONDS = 120.0
CLIENT_NAME = "bodha-gold-set"
UNAUTHORIZED = 401


class ApiError(RuntimeError):
    def __init__(self, method: str, path: str, status: int, message: str) -> None:
        super().__init__(f"{method} {path} answered {status}: {message}")
        self.status = status
        self.message = message


class SetupError(RuntimeError):
    pass


@dataclass(frozen=True)
class Credentials:
    email: str
    practice_id: str
    password: str = field(repr=False)
    totp_secret: str | None = field(default=None, repr=False)

    @classmethod
    def from_environment(cls, environ: Mapping[str, str]) -> Credentials:
        missing = [name for name in (ENV_EMAIL, ENV_PASSWORD, ENV_PRACTICE) if not environ.get(name, "").strip()]
        if missing:
            raise SetupError(f"set {', '.join(missing)} for the evaluation practice admin")
        secret = environ.get(ENV_TOTP, "").replace(" ", "").strip() or None
        return cls(environ[ENV_EMAIL].strip(), environ[ENV_PRACTICE].strip(), environ[ENV_PASSWORD], secret)


class BodhaApi:
    def __init__(self, client: httpx.Client, *, clock: Callable[[], float] = time.time) -> None:
        self._client = client
        self._clock = clock
        self._token: str | None = None

    @classmethod
    def open(cls, base_url: str) -> BodhaApi:
        client = httpx.Client(
            base_url=base_url.rstrip("/"), timeout=REQUEST_SECONDS, headers={"User-Agent": CLIENT_NAME}
        )
        return cls(client)

    def close(self) -> None:
        self._client.close()

    def sign_in(self, credentials: Credentials) -> dict[str, Any]:
        body = self._call(
            "POST", "/api/auth/login", json={"email": credentials.email, "password": credentials.password}
        )
        if "mfa" in body:
            body = self._second_step(body, credentials)
        self._token = body["access_token"]
        return body["user"]

    def get(self, path: str, params: Mapping[str, str] | None = None) -> Any:
        return self._authorized("GET", path, params=params)

    def post(self, path: str, json: Any = None) -> Any:
        return self._authorized("POST", path, json=json)

    def put(self, path: str, json: Any) -> Any:
        return self._authorized("PUT", path, json=json)

    def upload(self, path: str, form: Mapping[str, str], files: list[tuple[str, tuple[str, bytes, str]]]) -> Any:
        return self._authorized("POST", path, data=dict(form), files=files)

    def _second_step(self, challenge: Mapping[str, Any], credentials: Credentials) -> dict[str, Any]:
        if challenge["mfa"] != "verify":
            raise SetupError("this account has not set up two-step verification; set it up in the app first")
        if credentials.totp_secret is None:
            raise SetupError(f"this account uses two-step verification; set {ENV_TOTP}")
        code = pyotp.TOTP(credentials.totp_secret).at(self._clock())
        return self._call("POST", "/api/auth/mfa/verify", json={"mfa_token": challenge["mfa_token"], "code": code})

    def _authorized(self, method: str, path: str, **sent: Any) -> Any:
        if self._token is None:
            raise SetupError("sign in before calling the API")
        try:
            return self._call(method, path, **sent)
        except ApiError as error:
            if error.status != UNAUTHORIZED:
                raise
        self._token = self._call("POST", "/api/auth/refresh")["access_token"]
        return self._call(method, path, **sent)

    def _call(self, method: str, path: str, **sent: Any) -> Any:
        headers = {"Authorization": f"Bearer {self._token}"} if self._token else {}
        try:
            response = self._client.request(method, path, headers=headers, **sent)
        except httpx.HTTPError as error:
            raise ApiError(method, path, 0, type(error).__name__) from error
        if response.status_code >= 400:
            raise ApiError(method, path, response.status_code, _message(response))
        return response.json() if response.content else None


def _message(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return response.reason_phrase
    return str(body.get("message") or response.reason_phrase) if isinstance(body, dict) else response.reason_phrase
