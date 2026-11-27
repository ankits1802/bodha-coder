import pytest

from app.core.config import Settings
from app.core.errors import Invalid
from app.services.plans import (
    CATALOG,
    CHECKOUT_PLANS,
    PLAN_KEYS,
    annual_months_free,
    plan_for_price,
    plan_terms,
    price_cents,
    price_id,
    prices_complete,
)

STRIPE_PRICES = {
    "stripe_price_essentials_monthly": "price_ess_m",
    "stripe_price_essentials_annual": "price_ess_y",
    "stripe_price_professional_monthly": "price_pro_m",
    "stripe_price_professional_annual": "price_pro_y",
}


def settings(**values) -> Settings:
    base = {"secret_key": "test-only-secret-key-that-is-long-enough-000", "s3_bucket": "test-bucket"}
    return Settings(_env_file=None, **{**base, **values})


def test_the_catalog_holds_four_plans_and_only_two_are_bought_online():
    assert PLAN_KEYS == ("trial", "essentials", "professional", "enterprise")
    assert CHECKOUT_PLANS == ("essentials", "professional")


@pytest.mark.parametrize(
    ("key", "users", "providers"),
    [("trial", 5, 2), ("essentials", 5, 3), ("professional", None, 50), ("enterprise", None, None)],
)
def test_each_plan_names_its_user_and_provider_limits(key, users, providers):
    terms = plan_terms(key)
    assert (terms.max_users, terms.max_providers) == (users, providers)


def test_prices_are_per_active_provider_and_a_practice_pays_for_at_least_one():
    essentials, professional = plan_terms("essentials"), plan_terms("professional")
    assert price_cents(essentials, "monthly", 3) == 44_700
    assert price_cents(essentials, "annual", 3) == 447_000
    assert price_cents(professional, "monthly", 12) == 298_800
    assert price_cents(professional, "annual", 1) == 249_000
    assert price_cents(essentials, "monthly", 0) == 14_900


def test_paying_yearly_saves_two_months_on_both_paid_plans():
    assert annual_months_free(plan_terms("essentials")) == 2
    assert annual_months_free(plan_terms("professional")) == 2
    assert annual_months_free(plan_terms("trial")) is None


@pytest.mark.parametrize("key", ["trial", "enterprise"])
def test_the_trial_and_enterprise_have_no_listed_price(key):
    with pytest.raises(Invalid):
        price_cents(plan_terms(key), "monthly", 2)


def test_an_unknown_plan_is_refused():
    with pytest.raises(Invalid, match="basic"):
        plan_terms("basic")


def test_the_catalog_cannot_be_changed_at_run_time():
    with pytest.raises(TypeError):
        CATALOG["free"] = CATALOG["trial"]


def test_price_ids_come_from_settings_and_map_back_to_their_plan():
    found = settings(**STRIPE_PRICES)
    assert price_id(found, "stripe", "professional", "annual") == "price_pro_y"
    assert price_id(found, "stripe", "enterprise", "monthly") is None
    assert plan_for_price(found, "stripe", "price_ess_m") == ("essentials", "monthly")
    assert plan_for_price(found, "stripe", "price_unknown") is None
    assert plan_for_price(found, "paypal", "price_ess_m") is None


def test_a_provider_is_complete_only_with_all_four_prices():
    assert prices_complete(settings(**STRIPE_PRICES), "stripe")
    assert not prices_complete(settings(**{**STRIPE_PRICES, "stripe_price_professional_annual": "  "}), "stripe")
    assert not prices_complete(settings(**STRIPE_PRICES), "paypal")
