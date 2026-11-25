from __future__ import annotations

from typing import Annotated, Any

from fastapi import Cookie, Depends, Request, Response

from app.adapters.google_oidc import GoogleSignIn
from app.adapters.messenger import Messenger
from app.adapters.object_store import ObjectStore
from app.codes.icd import IcdCatalog
from app.core.config import get_settings
from app.models import User
from app.services.practice_setup import practice_checks

REFRESH_COOKIE = "bodha_refresh"
REFRESH_PATH = "/api/auth"
GOOGLE_COOKIE = "bodha_google"
GOOGLE_PATH = "/api/auth/google"


def store(request: Request) -> ObjectStore:
    return request.app.state.store


def messenger(request: Request) -> Messenger:
    return request.app.state.messenger


def icd(request: Request) -> IcdCatalog:
    return request.app.state.icd


def google(request: Request) -> GoogleSignIn:
    return request.app.state.google


def client_of(request: Request) -> tuple[str | None, str | None]:
    return (request.client.host if request.client else None), request.headers.get("user-agent")


Store = Annotated[ObjectStore, Depends(store)]
Mail = Annotated[Messenger, Depends(messenger)]
Icd = Annotated[IcdCatalog, Depends(icd)]
Google = Annotated[GoogleSignIn, Depends(google)]
RefreshCookie = Annotated[str | None, Cookie(alias=REFRESH_COOKIE)]
GoogleCookie = Annotated[str | None, Cookie(alias=GOOGLE_COOKIE)]


def set_refresh_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        REFRESH_COOKIE,
        token,
        max_age=settings.refresh_token_days * 86_400,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        path=REFRESH_PATH,
    )


def clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(REFRESH_COOKIE, path=REFRESH_PATH)


def set_google_cookie(response: Response, value: str, *, minutes: int) -> None:
    response.set_cookie(
        GOOGLE_COOKIE,
        value,
        max_age=minutes * 60,
        httponly=True,
        secure=get_settings().cookie_secure,
        samesite="lax",
        path=GOOGLE_PATH,
    )


def clear_google_cookie(response: Response) -> None:
    response.delete_cookie(
        GOOGLE_COOKIE, path=GOOGLE_PATH, httponly=True, secure=get_settings().cookie_secure, samesite="lax"
    )


def user_view(user: User, practice: Any | None) -> dict[str, Any]:
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "practice": None
        if practice is None
        else {
            "id": practice.id,
            "name": practice.name,
            "checks": practice_checks(practice),
            "idle_minutes": practice.idle_minutes,
            "time_zone": practice.time_zone,
        },
    }
