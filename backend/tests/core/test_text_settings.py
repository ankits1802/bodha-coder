import pytest

from app.core.config import Settings

ORIGINATION = "+18885550100"
TWILIO = {
    "twilio_account_sid": "AC00000000000000000000000000000000",
    "twilio_auth_token": "test-only",
    "twilio_from": ORIGINATION,
}


def settings(**values) -> Settings:
    base = {
        "secret_key": "test-only-secret-key-that-is-long-enough-000",
        "s3_bucket": "test-bucket",
        "app_environment": "production",
        "self_signup_enabled": False,
        "twilio_account_sid": None,
        "twilio_auth_token": None,
        "twilio_from": None,
        "sns_origination_number": None,
    }
    return Settings(_env_file=None, **{**base, **values})


@pytest.mark.parametrize(
    "values",
    [
        {"sms_transport": "twilio", **TWILIO},
        {"sms_transport": "sns", "sns_origination_number": ORIGINATION},
        {"sms_transport": "outbox", "app_environment": "development"},
        {"sms_transport": "twilio", "app_environment": "development"},
    ],
)
def test_texts_can_be_sent_through_a_set_up_transport_or_in_development(values):
    assert settings(**values).can_send_texts is True


@pytest.mark.parametrize(
    "values",
    [
        {"sms_transport": "outbox"},
        {"sms_transport": "outbox", "app_environment": "staging"},
        {"sms_transport": "twilio", **TWILIO, "twilio_from": None},
        {"sms_transport": "twilio", **TWILIO, "twilio_auth_token": ""},
        {"sms_transport": "sns"},
        {"sms_transport": "sns", **TWILIO},
        {"sms_transport": "twilio", "sns_origination_number": ORIGINATION},
    ],
)
def test_texts_cannot_be_sent_through_the_outbox_or_a_transport_missing_a_setting(values):
    assert settings(**values).can_send_texts is False
