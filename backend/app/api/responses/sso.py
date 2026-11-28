from typing import Literal

from app.models import SSO_NEW_PERSON_ROLES

from .view import View

__all__ = [
    "SsoAdmin",
    "SsoCertificate",
    "SsoConnection",
    "SsoDiscovery",
    "SsoDomain",
    "SsoHistoryRow",
    "SsoIdentityProvider",
    "SsoServiceProvider",
    "SsoSettings",
    "SsoTrialLink",
    "SsoTrialResult",
    "SsoVersion",
]

SsoMode = Literal["none", "optional", "required"]
NewPersonRole = Literal[SSO_NEW_PERSON_ROLES]


class SsoDiscovery(View):
    mode: SsoMode
    start_url: str | None


class SsoCertificate(View):
    value: str
    subject: str
    expires_at: str
    sha256: str


class SsoIdentityProvider(View):
    entity_id: str
    sso_url: str
    metadata_url: str | None
    certificates: list[SsoCertificate]


class SsoServiceProvider(View):
    entity_id: str
    acs_url: str
    metadata_url: str


class SsoVersion(View):
    version: int
    identity_provider: SsoIdentityProvider
    claim_ids: list[str]
    email_attribute: str | None
    name_attribute: str | None
    create_people: bool
    new_person_role: NewPersonRole | None
    required: bool
    break_glass: list[str]
    mfa_context: str | None


class SsoHistoryRow(View):
    version: int
    saved_at: str
    author_name: str


class SsoConnection(View):
    id: str
    service_provider: SsoServiceProvider
    current: SsoVersion | None
    history: list[SsoHistoryRow]


class SsoDomain(View):
    claim_id: str
    domain: str
    practice_name: str


class SsoAdmin(View):
    id: str
    name: str
    email: str
    ready: bool


class SsoSettings(View):
    connection: SsoConnection | None
    domains: list[SsoDomain]
    admins: list[SsoAdmin]


class SsoTrialLink(View):
    url: str


class SsoTrialResult(View):
    passed: bool
    reason: str | None
    domain: str | None
    in_domains: bool
    account: bool
    mfa: bool
    context_class: str | None
    name_found: bool
