from __future__ import annotations

from typing import Annotated, Any

from fastapi import Cookie, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.billing_contract import BillingProvider
from app.adapters.messenger import Messenger
from app.adapters.object_store import ObjectStore
from app.adapters.oidc import IdentityProvider
from app.codes.icd import IcdCatalog
from app.core.config import get_settings
from app.core.deps import billing_only_since
from app.core.errors import NotFound
from app.models import Practice, User
from app.services.auth import MfaChallenge, Tokens
from app.services.practice_setup import practice_checks

REFRESH_COOKIE = "bodha_refresh"
REFRESH_PATH = "/api/auth"
OIDC_COOKIE = "bodha_oidc"
OIDC_PATH = "/api/auth/{provider}"
SIGNUP_COOKIE = "bodha_signup"
SIGNUP_PATH = "/api/signup"


def store(request: Request) -> ObjectStore:
    return request.app.state.store


def messenger(request: Request) -> Messenger:
    return request.app.state.messenger


def icd(request: Request) -> IcdCatalog:
    return request.app.state.icd


def identity_providers(request: Request) -> dict[str, IdentityProvider]:
    return request.app.state.identity_providers


def identity_provider(request: Request, provider: str) -> IdentityProvider:
    found = identity_providers(request).get(provider)
    if found is None:
        raise NotFound("that sign-in provider is not known")
    return found


def billing_providers(request: Request) -> dict[str, BillingProvider]:
    return request.app.state.billing_providers


def client_of(request: Request) -> tuple[str | None, str | None]:
    return (request.client.host if request.client else None), request.headers.get("user-agent")


Store = Annotated[ObjectStore, Depends(store)]
Mail = Annotated[Messenger, Depends(messenger)]
Icd = Annotated[IcdCatalog, Depends(icd)]
IdentityProviders = Annotated[dict[str, IdentityProvider], Depends(identity_providers)]
ChosenProvider = Annotated[IdentityProvider, Depends(identity_provider)]
BillingProviders = Annotated[dict[str, BillingProvider], Depends(billing_providers)]
RefreshCookie = Annotated[str | None, Cookie(alias=REFRESH_COOKIE)]
OidcCookie = Annotated[str | None, Cookie(alias=OIDC_COOKIE)]
SignupCookie = Annotated[str | None, Cookie(alias=SIGNUP_COOKIE)]


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


def set_oidc_cookie(response: Response, provider: str, value: str, *, minutes: int) -> None:
    _set_lax_cookie(response, OIDC_COOKIE, value, path=OIDC_PATH.format(provider=provider), minutes=minutes)


def clear_oidc_cookie(response: Response, provider: str) -> None:
    _clear_lax_cookie(response, OIDC_COOKIE, path=OIDC_PATH.format(provider=provider))


def set_signup_cookie(response: Response, value: str, *, minutes: int) -> None:
    _set_lax_cookie(response, SIGNUP_COOKIE, value, path=SIGNUP_PATH, minutes=minutes)


def clear_signup_cookie(response: Response) -> None:
    _clear_lax_cookie(response, SIGNUP_COOKIE, path=SIGNUP_PATH)


def _set_lax_cookie(response: Response, name: str, value: str, *, path: str, minutes: int) -> None:
    secure = get_settings().cookie_secure
    response.set_cookie(name, value, max_age=minutes * 60, httponly=True, secure=secure, samesite="lax", path=path)


def _clear_lax_cookie(response: Response, name: str, *, path: str) -> None:
    response.delete_cookie(name, path=path, httponly=True, secure=get_settings().cookie_secure, samesite="lax")


async def signed_in_body(db: AsyncSession, response: Response, tokens: Tokens) -> dict[str, Any]:
    set_refresh_cookie(response, tokens.refresh)
    practice = await db.get(Practice, tokens.user.practice_id) if tokens.user.practice_id else None
    body: dict[str, Any] = {"access_token": tokens.access, "user": user_view(tokens.user, practice)}
    if tokens.recovery_codes:
        body["recovery_codes"] = list(tokens.recovery_codes)
    return body


def challenge_body(challenge: MfaChallenge) -> dict[str, str]:
    return {"mfa": challenge.step, "mfa_token": challenge.token}


def user_view(user: User, practice: Practice | None) -> dict[str, Any]:
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "billing_only": billing_only_since(user, practice) is not None,
        "practice": None
        if practice is None
        else {
            "id": practice.id,
            "name": practice.name,
            "checks": practice_checks(practice),
            "can_send_texts": get_settings().can_send_texts,
            "idle_minutes": practice.idle_minutes,
            "time_zone": practice.time_zone,
        },
    }
