from typing import Literal

from app.api.responses.base import PracticeRole, View
from app.api.responses.insights import Outcomes
from app.api.responses.plan import PayerOrganization, PlanKey, PlanSubscription
from app.models import (
    BILLING_INTERVALS,
    BILLING_PROVIDERS,
    JOIN_MODES,
    ORGANIZATION_STATUSES,
    PRACTICE_STATUSES,
    SUBSCRIPTION_STATUSES,
    VERIFICATION_METHODS,
)
from app.services.subscriptions import STANDINGS

__all__ = [
    "DomainClaimView",
    "HqOrganization",
    "HqOrganizationAdmin",
    "HqOrganizationHit",
    "HqOrganizationPage",
    "JoinOfferView",
    "JoinOutcome",
    "JoinPage",
    "JoinRequestRow",
    "MyOrganizationPractice",
    "OrganizationAdminRow",
    "OrganizationInsights",
    "OrganizationOverview",
    "OrganizationPlan",
    "OrganizationPracticeRow",
    "OrganizationPurged",
    "PayerOrganization",
    "PracticeInsight",
    "PracticeUsage",
    "VerifiedDomain",
]

PracticeStatus = Literal[PRACTICE_STATUSES]


class OrganizationPracticeRow(View):
    id: str
    name: str
    status: PracticeStatus
    plan: PlanKey
    renews_on: str | None
    combined_billing: bool
    users: int
    providers: int
    open: bool


class MyOrganizationPractice(OrganizationPracticeRow):
    my_role: PracticeRole | None


class OrganizationAdminRow(View):
    id: str
    name: str
    email: str


class OrganizationOverview(View):
    id: str
    name: str
    plan: PlanKey
    renews_on: str | None
    practices: list[MyOrganizationPractice]
    admins: list[OrganizationAdminRow]


class PracticeUsage(View):
    id: str
    name: str
    status: PracticeStatus
    providers: int
    provider_limit: int | None
    users: int
    user_limit: int | None


class OrganizationPlan(View):
    plan: PlanKey
    standing: Literal[STANDINGS]
    renews_on: str | None
    ending_soon: bool
    providers: int
    practices: list[PracticeUsage]
    subscription: PlanSubscription | None


class InsightFigures(View):
    notes: int
    approved: int
    approved_on_time: int
    estimated_notes: int
    outcomes: Outcomes
    difference: float


class PracticeInsight(InsightFigures):
    id: str
    name: str


class OrganizationInsights(View):
    days: int
    totals: InsightFigures
    practices: list[PracticeInsight]


class DomainClaimView(View):
    id: str
    domain: str
    practice_id: str
    practice_name: str
    verified: bool
    verified_at: str | None
    verified_via: Literal[VERIFICATION_METHODS] | None
    txt_record: str | None
    email_sent_to: str | None
    join_mode: Literal[JOIN_MODES]
    join_role: PracticeRole
    created_at: str


class JoinRequestRow(View):
    id: str
    name: str
    email: str
    domain: str
    suggested_role: PracticeRole
    created_at: str


class VerifiedDomain(View):
    domain: str
    practice_name: str


class JoinOfferView(View):
    practice_name: str
    mode: Literal["request", "auto"]


class JoinPage(View):
    email: str
    name: str
    own_practice_name: str
    join: JoinOfferView | None


class JoinOutcome(View):
    outcome: Literal["joined", "requested", "started"]


class HqOrganization(View):
    id: str
    name: str
    status: Literal[ORGANIZATION_STATUSES]
    plan: PlanKey
    renews_on: str | None
    practices: int
    combined_practices: int
    admins: int
    providers: int
    created_on: str
    closed_at: str | None
    purge_after: str | None
    purged_at: str | None
    billing_provider: Literal[BILLING_PROVIDERS] | None
    billing_status: Literal[SUBSCRIPTION_STATUSES] | None
    billing_interval: Literal[BILLING_INTERVALS] | None


class HqOrganizationAdmin(View):
    id: str
    name: str
    email: str
    mfa_enabled: bool
    last_active_at: str | None


class HqOrganizationPage(View):
    organization: HqOrganization
    practices: list[OrganizationPracticeRow]
    admins: list[HqOrganizationAdmin]
    plan: OrganizationPlan


class HqOrganizationHit(View):
    id: str
    name: str
    status: Literal[ORGANIZATION_STATUSES]


class OrganizationPurged(View):
    rows_removed: int
