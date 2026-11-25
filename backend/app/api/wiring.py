from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends, Request, Response

from app.adapters.messenger import Messenger
from app.adapters.object_store import ObjectStore
from app.codes.icd import IcdCatalog
from app.core.config import get_settings
from app.models import User

REFRESH_COOKIE = "bodha_refresh"
REFRESH_PATH = "/api/auth"


def store(request: Request) -> ObjectStore:
    return request.app.state.store


def messenger(request: Request) -> Messenger:
    return request.app.state.messenger


def icd(request: Request) -> IcdCatalog:
    return request.app.state.icd


Store = Annotated[ObjectStore, Depends(store)]
Mail = Annotated[Messenger, Depends(messenger)]
Icd = Annotated[IcdCatalog, Depends(icd)]


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
            "checks": practice.checks,
            "idle_minutes": practice.idle_minutes,
        },
    }
