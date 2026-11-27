from __future__ import annotations

from typing import Any, Literal
from urllib.parse import urlencode

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from app.adapters.oidc import ProviderIdentity
from app.adapters.oidc_providers import ProviderUnreachable
from app.api.responses.auth import SignInProviders
from app.api.responses.base import ExactRoute
from app.api.wiring import (
    ChosenProvider,
    IdentityProviders,
    OidcCookie,
    clear_oidc_cookie,
    client_of,
    set_oidc_cookie,
    set_refresh_cookie,
    set_signup_cookie,
)
from app.core.config import get_settings
from app.core.deps import Db, PlanEnded
from app.core.errors import RateLimited
from app.core.realms import CurrentSite, Site
from app.services import auth, identity_sign_in, signup

router = APIRouter(prefix="/auth", tags=["auth"], route_class=ExactRoute)
SIGNED_IN_FRAGMENT = "signed_in"
SIGN_IN = identity_sign_in.SIGN_IN_INTENT
Intent = Literal[identity_sign_in.INTENTS]
SIGN_UP_PAGE = "/sign-up/practice"


@router.get("/providers", response_model=SignInProviders)
async def providers(found: IdentityProviders, site: CurrentSite) -> dict[str, Any]:
    return {
        "providers": [name for name, provider in found.items() if provider.enabled],
        "signup": signup.signup_options(get_settings(), site),
    }


@router.get("/{provider}/start", response_class=RedirectResponse, status_code=302)
async def provider_start(chosen: ChosenProvider, site: CurrentSite, intent: Intent = SIGN_IN) -> RedirectResponse:
    try:
        started = await identity_sign_in.start(chosen, site, intent=intent)
    except ProviderUnreachable:
        return _to_sign_in(site, urlencode({"error": "failed", "provider": chosen.name}))
    response = RedirectResponse(started.url, status_code=302)
    set_oidc_cookie(response, chosen.name, started.cookie, minutes=identity_sign_in.START_MINUTES)
    return response


@router.get("/{provider}/callback", response_class=RedirectResponse, status_code=302)
async def provider_callback(
    request: Request,
    db: Db,
    chosen: ChosenProvider,
    site: CurrentSite,
    *,
    started: OidcCookie = None,
    code: str | None = None,
    state: str | None = None,
) -> RedirectResponse:
    returned = identity_sign_in.ProviderReturn(code=code, state=state, cookie=started)
    try:
        result = await identity_sign_in.finish(db, chosen, returned, site, client=client_of(request))
    except identity_sign_in.SignInRefused as error:
        response = _refused(site, error.reason, chosen.name)
    except PlanEnded:
        response = _refused(site, "plan_ended", chosen.name)
    except RateLimited:
        response = _refused(site, "rate_limited", chosen.name)
    else:
        response = _completed(site, result)
    clear_oidc_cookie(response, chosen.name)
    return response


def _completed(site: Site, result: auth.Tokens | auth.MfaChallenge | ProviderIdentity) -> RedirectResponse:
    if isinstance(result, ProviderIdentity):
        response = RedirectResponse(f"{site.url}{SIGN_UP_PAGE}", status_code=302)
        set_signup_cookie(response, signup.identity_token(result), minutes=signup.SIGNUP_MINUTES)
        return response
    if isinstance(result, auth.MfaChallenge):
        return _to_sign_in(site, urlencode({"mfa": result.token, "setup": "1" if result.step == "setup" else "0"}))
    response = _to_sign_in(site, SIGNED_IN_FRAGMENT)
    set_refresh_cookie(response, result.refresh)
    return response


def _refused(site: Site, reason: str, provider: str) -> RedirectResponse:
    return _to_sign_in(site, urlencode({"error": reason, "provider": provider}))


def _to_sign_in(site: Site, fragment: str) -> RedirectResponse:
    return RedirectResponse(f"{site.url}/sign-in#{fragment}", status_code=302)
