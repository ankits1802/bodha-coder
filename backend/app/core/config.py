from functools import lru_cache
from typing import Literal, Self

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

WEB_SCHEMES = ("https://", "http://")
BILLING_SETTINGS = (
    "stripe_secret_key",
    "stripe_webhook_secret",
    "stripe_price_essentials_monthly",
    "stripe_price_essentials_annual",
    "stripe_price_professional_monthly",
    "stripe_price_professional_annual",
    "paypal_client_id",
    "paypal_client_secret",
    "paypal_webhook_id",
    "paypal_plan_essentials_monthly",
    "paypal_plan_essentials_annual",
    "paypal_plan_professional_monthly",
    "paypal_plan_professional_annual",
)


class SignupNotReady(RuntimeError):
    pass


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)

    database_url: str = "postgresql+asyncpg://bodha:bodha@localhost:5432/bodha"
    secret_key: str = Field(min_length=32)
    app_url: str = "http://localhost:3000"
    cookie_secure: bool = True

    access_token_minutes: int = 15
    refresh_token_days: int = 7
    session_idle_minutes: int = 30
    mfa_issuer: str = "Bodha Coder"
    mfa_encryption_key: str | None = None
    google_client_id: str | None = None
    google_client_secret: SecretStr | None = None
    microsoft_client_id: str | None = None
    microsoft_client_secret: SecretStr | None = None
    microsoft_tenant: str = "common"
    yahoo_client_id: str | None = None
    yahoo_client_secret: SecretStr | None = None
    bootstrap_hq_email: str | None = None
    bootstrap_hq_password: str | None = None

    s3_bucket: str
    s3_endpoint_url: str | None = None
    s3_region: str = "us-east-1"
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None
    s3_server_side_encryption: str | None = "AES256"
    pdf_link_seconds: int = 60
    max_upload_mb: int = 40

    app_environment: Literal["development", "staging", "production"] = "production"
    gemini_backend: Literal["developer", "vertex", "demo"] = "developer"
    gemini_api_key: str | None = None
    google_cloud_project: str | None = None
    google_cloud_location: str | None = None
    gemini_model: str = "gemini-3.8-flash"
    gemini_timeout_seconds: int = 90
    ai_workers: int = 8
    ai_job_timeout_seconds: int = 600
    ai_max_attempts: int = 3
    ai_poll_seconds: float = 2.0

    email_transport: Literal["smtp", "ses", "outbox"] = "smtp"
    sms_transport: Literal["twilio", "sns", "outbox"] = "twilio"
    mail_from: str = "Bodha Coder <no-reply@bodhaai.co>"
    mail_outbox_dir: str | None = None
    aws_messaging_region: str = "us-east-1"
    ses_configuration_set: str | None = None
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None
    twilio_from: str | None = None

    self_signup_enabled: bool = True
    trial_days: int = Field(default=14, ge=1)
    trial_seats: int = Field(default=5, ge=1)
    terms_url: str | None = None
    baa_url: str | None = None
    privacy_url: str | None = None
    agreement_version: str = Field(default="unpublished", min_length=1, max_length=40)

    stripe_secret_key: SecretStr | None = None
    stripe_webhook_secret: SecretStr | None = None
    stripe_price_essentials_monthly: str | None = None
    stripe_price_essentials_annual: str | None = None
    stripe_price_professional_monthly: str | None = None
    stripe_price_professional_annual: str | None = None
    paypal_client_id: str | None = None
    paypal_client_secret: SecretStr | None = None
    paypal_webhook_id: str | None = None
    paypal_environment: Literal["sandbox", "live"] = "sandbox"
    paypal_plan_essentials_monthly: str | None = None
    paypal_plan_essentials_annual: str | None = None
    paypal_plan_professional_monthly: str | None = None
    paypal_plan_professional_annual: str | None = None
    billing_grace_days: int = Field(default=7, ge=0, le=60)

    turnaround_hours: int = 48
    addendum_link_hours: int = 72
    provider_session_minutes: int = 30

    @field_validator(*BILLING_SETTINGS, mode="before")
    @classmethod
    def _blank_is_unset(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value.strip() if isinstance(value, str) else value

    @field_validator("terms_url", "baa_url", "privacy_url", mode="before")
    @classmethod
    def _web_address_or_none(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        if not value.strip():
            return None
        if not value.strip().startswith(WEB_SCHEMES):
            raise ValueError("TERMS_URL, BAA_URL and PRIVACY_URL must be web addresses")
        return value.strip()

    @model_validator(mode="after")
    def _no_demo_model_in_production(self) -> Self:
        if self.gemini_backend == "demo" and self.app_environment == "production":
            raise ValueError("GEMINI_BACKEND=demo is refused when APP_ENVIRONMENT is production")
        return self

    def refuse_unready_signup(self) -> None:
        if self.app_environment == "production" and self.self_signup_enabled and not (self.baa_url and self.terms_url):
            raise SignupNotReady("SELF_SIGNUP_ENABLED needs BAA_URL and TERMS_URL when APP_ENVIRONMENT is production")


@lru_cache
def get_settings() -> Settings:
    return Settings()
