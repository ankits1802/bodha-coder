from __future__ import annotations

from typing import Annotated, Any
from urllib.parse import urlencode

from fastapi import APIRouter, Form, Query, Request, Response
from fastapi.responses import RedirectResponse

from app.adapters.saml_metadata import sp_metadata_xml
from app.adapters.saml_response import MAX_ENCODED_CHARS
from app.api.responses.base import ExactRoute, attachment, file_download
from app.api.responses.sso import SsoDiscovery
from app.api.routes.identity import SIGNED_IN_FRAGMENT, sign_in_redirect
from app.api.sso_bodies import SsoLookupBody
from app.api.wiring import SamlCookie, clear_saml_cookie, client_of, set_refresh_cookie, set_saml_cookie
from app.core.deps import Db
from app.core.errors import AppError, NotFound, RateLimited
from app.core.realms import CurrentSite, Site
from app.models import PRACTICE_REALM, SsoConnection
from app.services import auth, sso_sign_in
from app.services.sso_policy import service_provider
from app.services.sso_trial import TrialOutcome

router = APIRouter(prefix="/auth", tags=["auth"], route_class=ExactRoute)
METADATA_TYPE = "application/samlmetadata+xml"
METADATA_FILE = "bodha-assure-sp-metadata.xml"
SSO_PROVIDER = "sso"
RELAY_STATE_LENGTH = 512
SEE_OTHER = 303


@router.post("/sso", response_model=SsoDiscovery)
async def discover(body: SsoLookupBody, request: Request, db: Db, site: CurrentSite) -> dict[str, Any]:
    return await sso_sign_in.discover(db, str(body.email), site, client=client_of(request))


@router.get("/saml/{connection_id}/metadata", **file_download(METADATA_TYPE))
async def service_provider_metadata(connection_id: str, db: Db, site: CurrentSite) -> Response:
    connection = await db.get(SsoConnection, connection_id)
    if PRACTICE_REALM not in site.realms or connection is None or connection.removed_at is not None:
        raise NotFound("single sign-on is not set up here")
    return attachment(sp_metadata_xml(service_provider(connection.id)), METADATA_TYPE, METADATA_FILE)


@router.get("/saml/{connection_id}/start", response_class=RedirectResponse, status_code=302)
async def saml_start(
    connection_id: str,
    db: Db,
    site: CurrentSite,
    next_path: Annotated[str | None, Query(alias="next", max_length=RELAY_STATE_LENGTH)] = None,
    test: Annotated[str | None, Query(max_length=4000)] = None,
) -> RedirectResponse:
    if PRACTICE_REALM not in site.realms:
        return _refused(site, sso_sign_in.SsoRefusal("sso_failed"))
    try:
        started = await sso_sign_in.start(db, connection_id, next_path=next_path, test=test)
    except AppError:
        return _refused(site, sso_sign_in.SsoRefusal("sso_failed"))
    response = RedirectResponse(started.url, status_code=302)
    set_saml_cookie(response, connection_id, started.cookie, minutes=sso_sign_in.START_MINUTES)
    return response


@router.post("/saml/{connection_id}/acs", response_class=RedirectResponse, status_code=SEE_OTHER)
async def saml_acs(
    connection_id: str,
    request: Request,
    db: Db,
    site: CurrentSite,
    *,
    saml_response: Annotated[str, Form(alias="SAMLResponse", max_length=MAX_ENCODED_CHARS)],
    relay_state: Annotated[str | None, Form(alias="RelayState", max_length=RELAY_STATE_LENGTH)] = None,
    started: SamlCookie = None,
) -> RedirectResponse:
    posted = sso_sign_in.SamlPost(saml_response, relay_state, started)
    if PRACTICE_REALM not in site.realms:
        outcome: sso_sign_in.SsoOutcome = sso_sign_in.SsoRefusal("sso_failed")
    else:
        try:
            outcome = await sso_sign_in.finish(db, connection_id, posted, client=client_of(request))
        except RateLimited:
            outcome = sso_sign_in.SsoRefusal("rate_limited")
    response = _completed(site, outcome)
    clear_saml_cookie(response, connection_id)
    return response


def _completed(site: Site, outcome: sso_sign_in.SsoOutcome) -> RedirectResponse:
    if isinstance(outcome, sso_sign_in.SsoRefusal):
        return _refused(site, outcome)
    if isinstance(outcome, sso_sign_in.SsoBounce | TrialOutcome):
        target = outcome.path if isinstance(outcome, sso_sign_in.SsoBounce) else outcome.page
        return RedirectResponse(f"{site.url}{target}", status_code=SEE_OTHER)
    query = f"?{urlencode({'next': outcome.next_path})}" if outcome.next_path else ""
    result = outcome.result
    if isinstance(result, auth.MfaChallenge):
        fragment = urlencode({"mfa": result.token, "setup": "1" if result.step == "setup" else "0"})
        return sign_in_redirect(site, fragment, query=query, status_code=SEE_OTHER)
    response = sign_in_redirect(site, SIGNED_IN_FRAGMENT, query=query, status_code=SEE_OTHER)
    set_refresh_cookie(response, result.refresh)
    return response


def _refused(site: Site, refusal: sso_sign_in.SsoRefusal) -> RedirectResponse:
    fragment = urlencode({"error": refusal.reason, "provider": SSO_PROVIDER})
    return sign_in_redirect(site, fragment, status_code=SEE_OTHER)
