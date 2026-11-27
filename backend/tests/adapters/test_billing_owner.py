from app.adapters.billing_contract import CheckoutRequest
from app.adapters.paypal_billing import checkout_body
from app.adapters.paypal_billing import subscription_state as paypal_state
from app.adapters.stripe_billing import checkout_params
from app.adapters.stripe_billing import subscription_state as stripe_state

ORGANIZATION_METADATA = {"organization_id": "org-1", "plan": "essentials", "interval": "monthly"}


def organization_checkout() -> CheckoutRequest:
    return CheckoutRequest(
        practice_id=None,
        organization_id="org-1",
        plan="essentials",
        interval="monthly",
        price_id="price-1",
        quantity=7,
        email="owner@acme.example.com",
        customer_id=None,
        success_url="https://app.test/organizations/org-1/plan?checkout=done",
        cancel_url="https://app.test/organizations/org-1/plan?checkout=cancelled",
    )


def test_stripe_names_the_organization_in_the_checkout_and_reads_it_back():
    params = checkout_params(organization_checkout())
    assert params["client_reference_id"] == "org-1"
    assert params["subscription_data"]["metadata"] == ORGANIZATION_METADATA
    item = {"price": {"id": "price-1"}, "quantity": 7, "current_period_end": 1_900_000_000}
    state = stripe_state(
        {
            "id": "sub_1",
            "status": "active",
            "customer": "cus_1",
            "metadata": {"organization_id": "org-1"},
            "items": {"data": [item]},
        }
    )
    assert (state.organization_id, state.practice_id, state.quantity) == ("org-1", None, 7)


def test_paypal_marks_the_organization_in_the_custom_id_and_reads_it_back():
    assert checkout_body(organization_checkout())["custom_id"] == "organization:org-1"
    organization = paypal_state({"id": "I-1", "status": "ACTIVE", "custom_id": "organization:org-1", "plan_id": "P-1"})
    practice = paypal_state({"id": "I-2", "status": "ACTIVE", "custom_id": "practice-1", "plan_id": "P-1"})
    assert (organization.organization_id, organization.practice_id) == ("org-1", None)
    assert (practice.organization_id, practice.practice_id) == (None, "practice-1")
