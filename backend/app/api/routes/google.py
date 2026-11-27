from __future__ import annotations

from urllib.parse import urlencode

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from app.api.responses.auth import SignInProviders
from app.api.responses.base import ExactRoute
from app.api.wiring import Google, GoogleCookie, clear_google_cookie, client_of, set_google_cookie, set_refresh_cookie
from app.core.config import get_settings
from app.core.deps import Db, PlanEnded
from app.core.errors import RateLimited
from app.services import auth, google_sign_in

router = APIRouter(prefix="/auth", tags=["auth"], route_class=ExactRoute)
SIGNED_IN_FRAGMENT = "signed_in"


@router.get("/providers", response_model=SignInProviders)
async def providers(google: Google) -> dict[str, bool]:
    return {"google": google.enabled}


@router.get("/google/start", response_class=RedirectResponse, status_code=302)
async def google_start(google: Google) -> RedirectResponse:
    started = google_sign_in.start(google)
    response = RedirectResponse(started.url, status_code=302)
    set_google_cookie(response, started.cookie, minutes=google_sign_in.START_MINUTES)
    return response


@router.get("/google/callback", response_class=RedirectResponse, status_code=302)
async def google_callback(
    request: Request,
    db: Db,
    google: Google,
    *,
    started: GoogleCookie = None,
    code: str | None = None,
    state: str | None = None,
) -> RedirectResponse:
    ip, agent = client_of(request)
    returned = google_sign_in.GoogleReturn(code=code, state=state, cookie=started)
    try:
        result = await google_sign_in.finish(db, google, returned, ip=ip, agent=agent)
    except google_sign_in.GoogleSignInRefused as error:
        response = _to_sign_in(urlencode({"error": error.reason}))
    except PlanEnded:
        response = _to_sign_in(urlencode({"error": "plan_ended"}))
    except RateLimited:
        response = _to_sign_in(urlencode({"error": "rate_limited"}))
    else:
        response = _completed(result)
    clear_google_cookie(response)
    return response


def _completed(result: auth.Tokens | auth.MfaChallenge) -> RedirectResponse:
    if isinstance(result, auth.MfaChallenge):
        return _to_sign_in(urlencode({"mfa": result.token, "setup": "1" if result.step == "setup" else "0"}))
    response = _to_sign_in(SIGNED_IN_FRAGMENT)
    set_refresh_cookie(response, result.refresh)
    return response


def _to_sign_in(fragment: str) -> RedirectResponse:
    return RedirectResponse(f"{get_settings().app_url}/sign-in#{fragment}", status_code=302)
