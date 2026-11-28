from typing import Literal

from app.api.responses.base import PracticeRole, View
from app.api.responses.organizations import HqOrganizationHit
from app.api.responses.team import MemberStatus
from app.models import BILLING_INTERVALS, BILLING_PROVIDERS, PRACTICE_STATUSES, SUBSCRIPTION_STATUSES
from app.services.hq_admins import OUTCOMES
from app.services.plans import PLAN_KEYS
from app.services.practice_accounts import SIGNUP_SOURCES

__all__ = [
    "ActivityChange",
    "AdminAppointed",
    "AdminLinkSent",
    "AuditChain",
    "AuditVerification",
    "DemoRequestRow",
    "HqActivityEntry",
    "HqActivityPage",
    "HqOverview",
    "HqPerson",
    "HqPersonPractice",
    "HqPlace",
    "HqPractice",
    "HqPracticeHit",
    "HqPracticePage",
    "HqPracticePlace",
    "HqSearchPerson",
    "HqSearchResults",
    "HqTeamMember",
    "PracticePurged",
    "Renewal",
]


class HqOverview(View):
    practices: int
    people: int
    read_last_24h: int
    tokens_last_24h: int
    cost_last_24h_usd: float
    unpriced_last_24h: int
    failed_last_24h: int
    waiting: int
    running: int


class HqPractice(View):
    id: str
    name: str
    status: Literal[PRACTICE_STATUSES]
    plan: Literal[PLAN_KEYS]
    seats: int
    users: int
    providers: int
    waiting: int
    renews_on: str | None
    closed_at: str | None
    purge_after: str | None
    purged_at: str | None
    time_zone: str
    source: Literal[SIGNUP_SOURCES] | None
    signed_up_on: str
    failed_24h: int
    last_failure: str | None
    admin_name: str | None
    admin_email: str | None
    admin_status: MemberStatus | None
    billing_provider: Literal[BILLING_PROVIDERS] | None
    billing_status: Literal[SUBSCRIPTION_STATUSES] | None
    billing_interval: Literal[BILLING_INTERVALS] | None
    organization_id: str | None
    organization_name: str | None
    combined_billing: bool


class HqTeamMember(View):
    id: str
    name: str
    email: str
    status: MemberStatus
    mfa_enabled: bool
    last_active_at: str | None


class AdminAppointed(View):
    outcome: Literal[OUTCOMES]


class AdminLinkSent(View):
    sent: Literal["invite", "reset"]


class Renewal(View):
    renews_on: str | None
    plan: str


class HqPlace(View):
    code: str
    name: str
    active: bool


class ActivityChange(View):
    field: str
    before: str | int | None
    after: str | int | None


class HqActivityEntry(View):
    at: str
    actor: str
    action: str
    practice_id: str | None
    detail: str | None
    changes: list[ActivityChange] | None


class AuditChain(View):
    chain: Literal["access_log", "activity"]
    practice_id: str | None
    practice_name: str | None
    checked: int
    head_seq: int
    head_hash: str
    intact: bool
    broken_seq: int | None
    broken_id: str | None
    problem: Literal["missing rows", "broken link", "changed row"] | None


class AuditVerification(View):
    checked_at: str
    intact: bool
    chains: list[AuditChain]


class PracticePurged(View):
    access_log_entries: int
    access_log_sha256: str


class HqActivityPage(View):
    items: list[HqActivityEntry]
    total: int
    offset: int
    page_size: int
    actions: list[str]


class DemoRequestRow(View):
    id: str
    name: str
    email: str
    organization: str
    message: str | None
    received_at: str


class HqPracticePlace(View):
    code: str
    name: str
    active: bool
    providers: int
    notes: int


class HqPracticePage(View):
    practice: HqPractice
    places: list[HqPracticePlace]


class HqPerson(View):
    id: str
    name: str
    email: str
    role: PracticeRole
    status: MemberStatus
    mfa_enabled: bool
    last_active_at: str | None


class HqPracticeHit(View):
    id: str
    name: str
    status: Literal[PRACTICE_STATUSES]


class HqPersonPractice(View):
    id: str
    name: str
    role: PracticeRole


class HqSearchPerson(View):
    id: str
    name: str
    email: str
    practices: list[HqPersonPractice]


class HqSearchResults(View):
    organizations: list[HqOrganizationHit]
    practices: list[HqPracticeHit]
    people: list[HqSearchPerson]
    limit: int
