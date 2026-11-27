from typing import Literal

from app.api.responses.base import Omittable, Role, View

__all__ = [
    "Checks",
    "MfaChallenge",
    "MfaEnrolment",
    "PracticeSummary",
    "Preferences",
    "RecoveryCodeStatus",
    "RecoveryCodes",
    "SignInProviders",
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
    idle_minutes: int
    time_zone: str


class User(View):
    id: str
    name: str
    email: str
    role: Role
    practice: PracticeSummary | None


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


class SignInProviders(View):
    google: bool


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
