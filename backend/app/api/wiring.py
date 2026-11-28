from __future__ import annotations

from typing import Annotated, Any

from fastapi import Cookie, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.billing_contract import BillingProvider
from app.adapters.dns_txt import TxtResolver
from app.adapters.guarded_http import OutboundHttp
from app.adapters.messenger import Messenger
from app.adapters.object_store import ObjectStore
from app.adapters.oidc import IdentityProvider
from app.adapters.saml_fetch import MetadataSource
from app.adapters.seal_keys import RecordSigner
from app.adapters.sftp import FileLink
from app.codes.icd import IcdCatalog
from app.core.config import get_settings
from app.core.deps import Client, PracticeAccess, billing_only_since
from app.core.errors import NotFound
from app.models import HQ_REALM, User
from app.services.auth import MfaChallenge, Tokens
from app.services.memberships import practices_of
from app.services.organizations import organizations_of
from app.services.practice_setup import practice_checks
from app.services.signatures import SignatureTools

REFRESH_COOKIE = "bodha_refresh"
REFRESH_PATH = "/api/auth"
OIDC_COOKIE = "bodha_oidc"
OIDC_PATH = "/api/auth/{provider}"
SIGNUP_COOKIE = "bodha_signup"
SIGNUP_PATH = "/api/signup"
SAML_COOKIE = "bodha_saml"
SAML_PATH = "/api/auth/saml/{connection_id}"


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


def txt_resolver(request: Request) -> TxtResolver:
    return request.app.state.txt_resolver


def metadata_source(request: Request) -> MetadataSource:
    return request.app.state.metadata_source


def file_link(request: Request) -> FileLink:
    return request.app.state.file_link


def outbound(request: Request) -> OutboundHttp:
    return request.app.state.outbound


def record_signer(request: Request) -> RecordSigner:
    return request.app.state.signer


def signature_tools(request: Request) -> SignatureTools:
    return SignatureTools(request.app.state.store, request.app.state.image_model)


def client_of(request: Request) -> Client:
    return Client(request.client.host if request.client else None, request.headers.get("user-agent"))


Store = Annotated[ObjectStore, Depends(store)]
Mail = Annotated[Messenger, Depends(messenger)]
Icd = Annotated[IcdCatalog, Depends(icd)]
IdentityProviders = Annotated[dict[str, IdentityProvider], Depends(identity_providers)]
ChosenProvider = Annotated[IdentityProvider, Depends(identity_provider)]
BillingProviders = Annotated[dict[str, BillingProvider], Depends(billing_providers)]
Sealer = Annotated[RecordSigner, Depends(record_signer)]
Link = Annotated[FileLink, Depends(file_link)]
Outbound = Annotated[OutboundHttp, Depends(outbound)]
Resolver = Annotated[TxtResolver, Depends(txt_resolver)]
Metadata = Annotated[MetadataSource, Depends(metadata_source)]
SigningTools = Annotated[SignatureTools, Depends(signature_tools)]
RefreshCookie = Annotated[str | None, Cookie(alias=REFRESH_COOKIE)]
OidcCookie = Annotated[str | None, Cookie(alias=OIDC_COOKIE)]
SignupCookie = Annotated[str | None, Cookie(alias=SIGNUP_COOKIE)]
SamlCookie = Annotated[str | None, Cookie(alias=SAML_COOKIE)]


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


def set_saml_cookie(response: Response, connection_id: str, value: str, *, minutes: int) -> None:
    path = SAML_PATH.format(connection_id=connection_id)
    response.set_cookie(
        SAML_COOKIE, value, max_age=minutes * 60, httponly=True, secure=True, samesite="none", path=path
    )


def clear_saml_cookie(response: Response, connection_id: str) -> None:
    path = SAML_PATH.format(connection_id=connection_id)
    response.delete_cookie(SAML_COOKIE, path=path, httponly=True, secure=True, samesite="none")


def _set_lax_cookie(response: Response, name: str, value: str, *, path: str, minutes: int) -> None:
    secure = get_settings().cookie_secure
    response.set_cookie(name, value, max_age=minutes * 60, httponly=True, secure=secure, samesite="lax", path=path)


def _clear_lax_cookie(response: Response, name: str, *, path: str) -> None:
    response.delete_cookie(name, path=path, httponly=True, secure=get_settings().cookie_secure, samesite="lax")


async def signed_in_body(db: AsyncSession, response: Response, tokens: Tokens) -> dict[str, Any]:
    set_refresh_cookie(response, tokens.refresh)
    body: dict[str, Any] = {"access_token": tokens.access, "user": await user_view(db, tokens.user, tokens.standing)}
    if tokens.recovery_codes:
        body["recovery_codes"] = list(tokens.recovery_codes)
    return body


def challenge_body(challenge: MfaChallenge) -> dict[str, str]:
    return {"mfa": challenge.step, "mfa_token": challenge.token}


async def sign_in_body(db: AsyncSession, response: Response, result: Tokens | MfaChallenge) -> dict[str, Any]:
    if isinstance(result, MfaChallenge):
        return challenge_body(result)
    return await signed_in_body(db, response, result)


async def user_view(db: AsyncSession, user: User, standing: PracticeAccess) -> dict[str, Any]:
    practice = standing.practice
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role": standing.role,
        "billing_only": billing_only_since(standing.role, practice) is not None,
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
        "practices": [
            {"id": choice.id, "name": choice.name, "role": choice.role} for choice in await practices_of(db, user)
        ],
        **await _organizations_view(db, user),
    }


async def _organizations_view(db: AsyncSession, user: User) -> dict[str, Any]:
    if user.realm == HQ_REALM:
        return {}
    choices = await organizations_of(db, user)
    return {"organizations": [{"id": choice.id, "name": choice.name, "role": choice.role} for choice in choices]}
