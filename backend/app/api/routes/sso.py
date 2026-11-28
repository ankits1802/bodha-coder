from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.api.responses.base import ExactRoute
from app.api.responses.sso import SsoIdentityProvider, SsoSettings, SsoTrialLink, SsoTrialResult
from app.api.routes.organizations import OrganizationAdmin
from app.api.sso_bodies import SsoMetadataBody, SsoSettingsBody, SsoTrialResultBody
from app.api.wiring import Metadata
from app.core.deps import Actor, Db, require
from app.core.roles import ADMINS
from app.services import sso_settings, sso_trial
from app.services.domain_claims import ClaimScope
from app.services.sso_settings import IdentityProviderValues, SsoValues

router = APIRouter(tags=["single sign-on"], route_class=ExactRoute)
Admin = Annotated[Actor, Depends(require(*ADMINS))]
PRACTICE_SSO = "/practice/sso"
ORGANIZATION_SSO = "/organizations/{organization_id}/sso"


def _practice(actor: Actor) -> ClaimScope:
    return ClaimScope(actor.practice_id, None)


def _organization(session: OrganizationAdmin) -> ClaimScope:
    return ClaimScope(None, session.organization.id)


def _values(body: SsoSettingsBody) -> SsoValues:
    provider = body.identity_provider
    return SsoValues(
        provider=IdentityProviderValues(
            provider.entity_id, provider.sso_url, tuple(provider.certificates), provider.metadata_url
        ),
        claim_ids=tuple(body.claim_ids),
        email_attribute=body.email_attribute,
        name_attribute=body.name_attribute,
        create_people=body.create_people,
        new_person_role=body.new_person_role,
        required=body.required,
        break_glass=tuple(body.break_glass),
        mfa_context=body.mfa_context,
    )


@router.get(PRACTICE_SSO, response_model=SsoSettings)
async def practice_sso(db: Db, actor: Admin) -> dict[str, Any]:
    return await sso_settings.sso_view(db, _practice(actor))


@router.post(PRACTICE_SSO, response_model=SsoSettings)
async def set_up_practice_sso(db: Db, actor: Admin) -> dict[str, Any]:
    return await sso_settings.set_up_sso(db, actor, _practice(actor))


@router.put(PRACTICE_SSO, response_model=SsoSettings)
async def save_practice_sso(body: SsoSettingsBody, db: Db, actor: Admin) -> dict[str, Any]:
    return await sso_settings.save_sso(db, actor, _practice(actor), _values(body))


@router.delete(PRACTICE_SSO, response_model=SsoSettings)
async def remove_practice_sso(db: Db, actor: Admin) -> dict[str, Any]:
    return await sso_settings.remove_sso(db, actor, _practice(actor))


@router.post(f"{PRACTICE_SSO}/metadata", response_model=SsoIdentityProvider)
async def read_practice_metadata(body: SsoMetadataBody, db: Db, actor: Admin, source: Metadata) -> dict[str, Any]:
    return await sso_settings.preview_metadata(db, source, _practice(actor), xml=body.xml, url=body.url)


@router.post(f"{PRACTICE_SSO}/test", response_model=SsoTrialLink)
async def test_practice_sso(db: Db, actor: Admin) -> dict[str, str]:
    return await sso_trial.trial_link(db, actor, _practice(actor))


@router.post(f"{PRACTICE_SSO}/test-result", response_model=SsoTrialResult)
async def practice_sso_result(body: SsoTrialResultBody, db: Db, actor: Admin) -> dict[str, Any]:
    return await sso_trial.scoped_trial_result(db, actor, _practice(actor), body.token)


@router.get(ORGANIZATION_SSO, response_model=SsoSettings)
async def organization_sso(db: Db, session: OrganizationAdmin) -> dict[str, Any]:
    return await sso_settings.sso_view(db, _organization(session))


@router.post(ORGANIZATION_SSO, response_model=SsoSettings)
async def set_up_organization_sso(db: Db, session: OrganizationAdmin) -> dict[str, Any]:
    return await sso_settings.set_up_sso(db, session.actor, _organization(session))


@router.put(ORGANIZATION_SSO, response_model=SsoSettings)
async def save_organization_sso(body: SsoSettingsBody, db: Db, session: OrganizationAdmin) -> dict[str, Any]:
    return await sso_settings.save_sso(db, session.actor, _organization(session), _values(body))


@router.delete(ORGANIZATION_SSO, response_model=SsoSettings)
async def remove_organization_sso(db: Db, session: OrganizationAdmin) -> dict[str, Any]:
    return await sso_settings.remove_sso(db, session.actor, _organization(session))


@router.post(f"{ORGANIZATION_SSO}/metadata", response_model=SsoIdentityProvider)
async def read_organization_metadata(
    body: SsoMetadataBody, db: Db, session: OrganizationAdmin, source: Metadata
) -> dict[str, Any]:
    scope = _organization(session)
    return await sso_settings.preview_metadata(db, source, scope, xml=body.xml, url=body.url)


@router.post(f"{ORGANIZATION_SSO}/test", response_model=SsoTrialLink)
async def test_organization_sso(db: Db, session: OrganizationAdmin) -> dict[str, str]:
    return await sso_trial.trial_link(db, session.actor, _organization(session))


@router.post(f"{ORGANIZATION_SSO}/test-result", response_model=SsoTrialResult)
async def organization_sso_result(body: SsoTrialResultBody, db: Db, session: OrganizationAdmin) -> dict[str, Any]:
    return await sso_trial.scoped_trial_result(db, session.actor, _organization(session), body.token)
