from typing import Literal

from app.api.responses.base import Omittable, View
from app.models import BILLING_INTERVALS, BILLING_PROVIDERS, SUBSCRIPTION_STATUSES
from app.services.plans import PLAN_KEYS, PRICINGS
from app.services.subscriptions import MANAGE_ACTIONS, STANDINGS

__all__ = [
    "BillingInterval",
    "BillingProviderName",
    "PayerOrganization",
    "PlanCatalog",
    "PlanKey",
    "PlanStatus",
    "PlanSubscription",
    "PlanTerms",
    "RedirectLink",
]

PlanKey = Literal[PLAN_KEYS]
BillingProviderName = Literal[BILLING_PROVIDERS]
BillingInterval = Literal[BILLING_INTERVALS]


class PlanTerms(View):
    key: PlanKey
    pricing: Literal[PRICINGS]
    monthly_cents: int | None
    annual_cents: int | None
    annual_months_free: int | None
    max_users: int | None
    max_providers: int | None


class PlanCatalog(View):
    plans: list[PlanTerms]
    providers: list[BillingProviderName]
    trial_days: int


class PlanSubscription(View):
    provider: BillingProviderName
    interval: BillingInterval
    status: Literal[SUBSCRIPTION_STATUSES]
    cancel_at_period_end: bool
    current_period_end: str | None
    quantity: int
    managed_by: Literal[MANAGE_ACTIONS]


class PayerOrganization(View):
    id: str
    name: str


class PlanStatus(View):
    plan: PlanKey
    standing: Literal[STANDINGS]
    renews_on: str | None
    trial_days_left: int | None
    ending_soon: bool
    users: int
    user_limit: int | None
    providers: int
    provider_limit: int | None
    subscription: PlanSubscription | None
    organization: Omittable[PayerOrganization] = None


class RedirectLink(View):
    url: str
