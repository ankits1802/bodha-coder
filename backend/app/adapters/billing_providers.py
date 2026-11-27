from __future__ import annotations

from app.adapters.billing_contract import BillingProvider
from app.adapters.paypal_billing import PAYPAL, PayPalBilling, PayPalConfig, paypal_client
from app.adapters.stripe_billing import STRIPE, StripeBilling, StripeSdk
from app.core.config import Settings

__all__ = ["PROVIDER_NAMES", "build_billing_providers"]

PROVIDER_NAMES = (STRIPE, PAYPAL)


def build_billing_providers(settings: Settings) -> dict[str, BillingProvider]:
    providers: dict[str, BillingProvider] = {}
    if settings.stripe_secret_key and settings.stripe_webhook_secret:
        api = StripeSdk(settings.stripe_secret_key.get_secret_value())
        providers[STRIPE] = StripeBilling(
            api,
            webhook_secret=settings.stripe_webhook_secret.get_secret_value(),
            portal_configuration=settings.stripe_portal_configuration,
        )
    if settings.paypal_client_id and settings.paypal_client_secret and settings.paypal_webhook_id:
        config = PayPalConfig(
            settings.paypal_client_id,
            settings.paypal_client_secret.get_secret_value(),
            settings.paypal_webhook_id,
            settings.paypal_environment,
        )
        providers[PAYPAL] = PayPalBilling(config, paypal_client(settings.paypal_environment))
    return providers
