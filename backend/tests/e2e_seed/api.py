from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import get_settings, site_host

__all__ = ["API_URL_VARIABLE", "Api", "Caller", "SeedFailed", "admin_host", "practice_host"]

API_URL_VARIABLE = "E2E_API_URL"
DEFAULT_API_URL = "http://127.0.0.1:8000"
REQUEST_SECONDS = 60.0


class SeedFailed(RuntimeError):
    pass


@dataclass(frozen=True)
class Caller:
    token: str | None
    host: str


def practice_host() -> str:
    return site_host(get_settings().app_url)


def admin_host() -> str:
    settings = get_settings()
    if not settings.admin_url:
        raise SeedFailed("set ADMIN_URL so HQ has its own host")
    return site_host(settings.admin_url)


class Api:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    @staticmethod
    def client() -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=os.environ.get(API_URL_VARIABLE, DEFAULT_API_URL), timeout=REQUEST_SECONDS)

    async def send(self, caller: Caller, method: str, path: str, **options: Any) -> Any:
        response = await self._request(caller, method, path, **options)
        return response.json() if response.content else None

    async def download(self, caller: Caller, path: str) -> bytes:
        return (await self._request(caller, "GET", path)).content

    async def _request(self, caller: Caller, method: str, path: str, **options: Any) -> httpx.Response:
        headers = {"Host": caller.host}
        if caller.token:
            headers["Authorization"] = f"Bearer {caller.token}"
        response = await self._client.request(method, path, headers=headers, **options)
        if response.is_error:
            raise SeedFailed(f"{method} {path} answered {response.status_code}: {response.text}")
        return response
