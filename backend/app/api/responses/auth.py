from typing import Literal

from app.adapters.oidc_providers import PROVIDER_NAMES
from app.api.responses.base import Omittable, PracticeRole, Role, View
from app.models import ORGANIZATION_ROLES

__all__ = [
    "Checks",
    "MfaChallenge",
    "MfaEnrolment",
    "OrganizationChoice",
    "PracticeChoice",
    "PracticeSummary",
    "Preferences",
    "RecoveryCodeStatus",
    "RecoveryCodes",
    "IdentityProviderName",
    "SignInProviders",
    "SignUpOptions",
    "SignedIn",
    "SignedInDevice",
    "User",
]


class Checks(View):
    em: bool
    icd: bool
    cdi: bool
    audit: bool
    mips: bool
    hcc: bool


class PracticeSummary(View):
    id: str
    name: str
    checks: Checks
    can_send_texts: bool
    idle_minutes: int
    time_zone: str


class PracticeChoice(View):
    id: str
    name: str
    role: PracticeRole


class OrganizationChoice(View):
    id: str
    name: str
    role: Literal[ORGANIZATION_ROLES]


class User(View):
    id: str
    name: str
    email: str
    role: Role
    billing_only: bool
    practice: PracticeSummary | None
    practices: list[PracticeChoice]
    organizations: Omittable[list[OrganizationChoice]] = None


class SignedIn(View):
    access_token: str
    user: User
    recovery_codes: Omittable[list[str]] = None


class MfaChallenge(View):
    mfa: Literal["setup", "verify"]
    mfa_token: str


class MfaEnrolment(View):
    secret: str
    uri: str
    qr_image: str


IdentityProviderName = Literal[PROVIDER_NAMES]


class SignUpOptions(View):
    enabled: bool
    terms_url: str | None
    baa_url: str | None
    privacy_url: str | None
    test_data_only: bool


class SignInProviders(View):
    providers: list[IdentityProviderName]
    signup: SignUpOptions


class SignedInDevice(View):
    id: str
    created_at: str
    last_used_at: str
    ip: str | None
    user_agent: str | None
    current: bool


class RecoveryCodeStatus(View):
    enabled: bool
    remaining: int


class RecoveryCodes(View):
    codes: list[str]


class Preferences(View):
    notify_digest: bool
