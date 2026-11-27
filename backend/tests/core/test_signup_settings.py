import pytest
from pydantic import ValidationError

import app.main
from app.core.config import Settings, SignupNotReady

TERMS = "https://bodha.example.com/terms"
BAA = "https://bodha.example.com/baa"


def settings(**values) -> Settings:
    base = {
        "secret_key": "test-only-secret-key-that-is-long-enough-000",
        "s3_bucket": "test-bucket",
        "app_environment": "production",
        "self_signup_enabled": True,
        "terms_url": TERMS,
        "baa_url": BAA,
    }
    return Settings(_env_file=None, **{**base, **values})


@pytest.mark.parametrize("missing", ["baa_url", "terms_url"])
def test_production_refuses_to_start_self_sign_up_without_the_baa_and_the_terms(missing):
    with pytest.raises(SignupNotReady, match="BAA_URL and TERMS_URL"):
        settings(**{missing: None}).refuse_unready_signup()


@pytest.mark.parametrize(
    "values",
    [
        {},
        {"self_signup_enabled": False, "baa_url": None, "terms_url": None},
        {"app_environment": "staging", "baa_url": None},
    ],
)
def test_sign_up_starts_with_both_links_off_or_outside_production(values):
    settings(**values).refuse_unready_signup()


def test_a_blank_link_counts_as_unset_and_anything_but_a_web_address_is_refused():
    assert settings(baa_url="  ", privacy_url="").baa_url is None
    with pytest.raises(ValidationError):
        settings(terms_url="javascript:alert(1)")


def test_trial_length_and_seats_default_to_fourteen_days_and_five_seats():
    found = settings()
    assert (found.trial_days, found.trial_seats, found.agreement_version) == (14, 5, "unpublished")


async def test_the_api_refuses_to_start_when_production_sign_up_has_no_baa(monkeypatch):
    monkeypatch.setattr(app.main, "get_settings", lambda: settings(baa_url=None))
    with pytest.raises(SignupNotReady):
        async with app.main.lifespan(app.main.app):
            pass
