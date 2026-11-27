from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from app.core.config import Settings
from app.core.errors import Invalid
from app.models import BILLING_INTERVALS, BILLING_PROVIDERS

__all__ = [
    "CATALOG",
    "CHECKOUT_PLANS",
    "ENTERPRISE",
    "ESSENTIALS",
    "PLAN_KEYS",
    "PRICE_SETTING_PREFIX",
    "PRICINGS",
    "PROFESSIONAL",
    "TRIAL",
    "PlanTerms",
    "annual_months_free",
    "plan_for_price",
    "plan_terms",
    "price_cents",
    "price_id",
    "prices_complete",
]

TRIAL = "trial"
ESSENTIALS = "essentials"
PROFESSIONAL = "professional"
ENTERPRISE = "enterprise"
MONTHLY, ANNUAL = BILLING_INTERVALS
MONTHS_PER_YEAR = 12
PRICE_SETTING_PREFIX = {"stripe": "stripe_price", "paypal": "paypal_plan"}
PRICINGS = ("free", "per_provider", "custom")
FREE, PER_PROVIDER, CUSTOM = PRICINGS


@dataclass(frozen=True)
class PlanTerms:
    key: str
    name: str
    pricing: str
    monthly_cents: int | None
    annual_cents: int | None
    max_users: int | None
    max_providers: int | None

    @property
    def self_checkout(self) -> bool:
        return self.pricing == PER_PROVIDER


CATALOG: Mapping[str, PlanTerms] = MappingProxyType(
    {
        TRIAL: PlanTerms(TRIAL, "Trial", FREE, None, None, max_users=5, max_providers=2),
        ESSENTIALS: PlanTerms(ESSENTIALS, "Essentials", PER_PROVIDER, 14_900, 149_000, max_users=5, max_providers=3),
        PROFESSIONAL: PlanTerms(
            PROFESSIONAL, "Professional", PER_PROVIDER, 24_900, 249_000, max_users=None, max_providers=50
        ),
        ENTERPRISE: PlanTerms(ENTERPRISE, "Enterprise", CUSTOM, None, None, max_users=None, max_providers=None),
    }
)
PLAN_KEYS = tuple(CATALOG)
CHECKOUT_PLANS = tuple(key for key, terms in CATALOG.items() if terms.self_checkout)


def plan_terms(key: str) -> PlanTerms:
    terms = CATALOG.get(key)
    if terms is None:
        raise Invalid(f"unknown plan {key}")
    return terms


def price_cents(terms: PlanTerms, interval: str, providers: int) -> int:
    each = terms.monthly_cents if interval == MONTHLY else terms.annual_cents
    if each is None:
        raise Invalid(f"the {terms.name} plan has no listed price")
    return each * max(1, providers)


def annual_months_free(terms: PlanTerms) -> int | None:
    if terms.monthly_cents is None or terms.annual_cents is None:
        return None
    return (terms.monthly_cents * MONTHS_PER_YEAR - terms.annual_cents) // terms.monthly_cents


def price_id(settings: Settings, provider: str, plan: str, interval: str) -> str | None:
    if provider not in BILLING_PROVIDERS or plan not in CHECKOUT_PLANS or interval not in BILLING_INTERVALS:
        return None
    return getattr(settings, f"{PRICE_SETTING_PREFIX[provider]}_{plan}_{interval}")


def prices_complete(settings: Settings, provider: str) -> bool:
    return all(
        price_id(settings, provider, plan, interval) for plan in CHECKOUT_PLANS for interval in BILLING_INTERVALS
    )


def plan_for_price(settings: Settings, provider: str, found: str | None) -> tuple[str, str] | None:
    if not found:
        return None
    for plan in CHECKOUT_PLANS:
        for interval in BILLING_INTERVALS:
            if price_id(settings, provider, plan, interval) == found:
                return plan, interval
    return None
