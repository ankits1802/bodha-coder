from __future__ import annotations

from typing import Annotated, Literal

from pydantic import EmailStr, Field

from app.adapters.saml_metadata import MAX_CERTIFICATES
from app.adapters.saml_xml import MAX_XML_BYTES
from app.api.bodies import Body
from app.models import SSO_ATTRIBUTE_LENGTH, SSO_ENTITY_ID_LENGTH, SSO_NEW_PERSON_ROLES, SSO_URL_LENGTH

__all__ = [
    "IdentityProviderBody",
    "SsoLookupBody",
    "SsoMetadataBody",
    "SsoSettingsBody",
    "SsoTrialResultBody",
]

CERTIFICATE_CHARS = 20_000
ID_LENGTH = 36
MAX_DOMAINS = 50
MAX_BREAK_GLASS = 20
TOKEN_LENGTH = 4000

Certificate = Annotated[str, Field(min_length=1, max_length=CERTIFICATE_CHARS)]
RecordId = Annotated[str, Field(min_length=1, max_length=ID_LENGTH)]
Attribute = Annotated[str | None, Field(max_length=SSO_ATTRIBUTE_LENGTH)]


class SsoLookupBody(Body):
    email: EmailStr


class SsoMetadataBody(Body):
    xml: str | None = Field(default=None, min_length=1, max_length=MAX_XML_BYTES)
    url: str | None = Field(default=None, min_length=9, max_length=SSO_URL_LENGTH)


class IdentityProviderBody(Body):
    entity_id: str = Field(min_length=1, max_length=SSO_ENTITY_ID_LENGTH)
    sso_url: str = Field(min_length=9, max_length=SSO_URL_LENGTH)
    certificates: list[Certificate] = Field(min_length=1, max_length=MAX_CERTIFICATES)
    metadata_url: str | None = Field(default=None, max_length=SSO_URL_LENGTH)


class SsoSettingsBody(Body):
    identity_provider: IdentityProviderBody
    claim_ids: list[RecordId] = Field(default_factory=list, max_length=MAX_DOMAINS)
    email_attribute: Attribute = None
    name_attribute: Attribute = None
    create_people: bool = False
    new_person_role: Literal[SSO_NEW_PERSON_ROLES] = "viewer"
    required: bool = False
    break_glass: list[RecordId] = Field(default_factory=list, max_length=MAX_BREAK_GLASS)
    mfa_context: Attribute = None


class SsoTrialResultBody(Body):
    token: str = Field(min_length=16, max_length=TOKEN_LENGTH)
