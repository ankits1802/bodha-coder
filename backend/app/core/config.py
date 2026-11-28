import re
from decimal import Decimal
from functools import lru_cache
from typing import Literal, Self
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.model_prices import ModelPrice

WEB_SCHEMES = ("https://", "http://")
HOST_NAME = re.compile(r"^(?=.{4,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z][a-z0-9-]{0,61}[a-z0-9]$")
SENTRY_DSN = re.compile(r"^https://[0-9a-f]+@[a-z0-9.-]+(?::[0-9]+)?/[0-9]+$")
RETENTION_FLOOR_DAYS = 2557
DEFAULT_GEMINI_MODEL = "gemini-3.8-flash"
DEFAULT_MODEL_PRICES = {DEFAULT_GEMINI_MODEL: ModelPrice(input=Decimal("0.50"), output=Decimal("3.00"))}
BILLING_SETTINGS = (
    "stripe_secret_key",
    "stripe_webhook_secret",
    "stripe_price_essentials_monthly",
    "stripe_price_essentials_annual",
    "stripe_price_professional_monthly",
    "stripe_price_professional_annual",
    "stripe_portal_configuration",
    "paypal_client_id",
    "paypal_client_secret",
    "paypal_webhook_id",
    "paypal_plan_essentials_monthly",
    "paypal_plan_essentials_annual",
    "paypal_plan_professional_monthly",
    "paypal_plan_professional_annual",
)
TEXT_SETTINGS = {
    "twilio": ("twilio_account_sid", "twilio_auth_token", "twilio_from"),
    "sns": ("sns_origination_number",),
}


class SignupNotReady(RuntimeError):
    pass


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)

    database_url: str = "postgresql+asyncpg://bodha:bodha@localhost:5432/bodha"
    migration_database_url: str | None = None
    app_version: str = Field(default="unversioned", min_length=1, max_length=64)
    retention_days: int = Field(default=RETENTION_FLOOR_DAYS, ge=RETENTION_FLOOR_DAYS)
    secret_key: str = Field(min_length=32)
    app_url: str = "http://localhost:3000"
    admin_url: str = ""
    forwarded_allow_ips: str = "127.0.0.1"
    cookie_secure: bool = True

    access_token_minutes: int = 15
    refresh_token_days: int = 30
    session_idle_minutes: int = 10_080
    mfa_issuer: str = "Bodha Assure"
    mfa_encryption_key: str | None = None
    clearinghouse_encryption_key: str | None = None
    clearinghouse_timeout_seconds: int = Field(default=30, ge=5, le=120)
    ehr_key_encryption_key: str | None = None
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
    gemini_model: str = DEFAULT_GEMINI_MODEL
    model_prices: dict[str, ModelPrice] = Field(default_factory=lambda: dict(DEFAULT_MODEL_PRICES))
    gemini_timeout_seconds: int = 90
    ai_workers: int = 8
    ai_job_timeout_seconds: int = 600
    ai_max_attempts: int = 3
    ai_poll_seconds: float = 2.0

    email_transport: Literal["smtp", "ses", "outbox"] = "smtp"
    sms_transport: Literal["twilio", "sns", "outbox"] = "twilio"
    mail_from: str = "Bodha Assure <no-reply@bodhaai.co>"
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
    sns_origination_number: str | None = None
    email_intake_domain: str = ""
    email_intake_bucket: str = ""
    sentry_dsn: str = ""

    self_signup_enabled: bool = True
    trial_days: int = Field(default=14, ge=1)
    trial_seats: int = Field(default=5, ge=1)
    terms_url: str | None = None
    baa_url: str | None = None
    privacy_url: str | None = None
    agreement_version: str = Field(default="unpublished", min_length=1, max_length=40)
    signing_key_id: str | None = None

    stripe_secret_key: SecretStr | None = None
    stripe_webhook_secret: SecretStr | None = None
    stripe_price_essentials_monthly: str | None = None
    stripe_price_essentials_annual: str | None = None
    stripe_price_professional_monthly: str | None = None
    stripe_price_professional_annual: str | None = None
    stripe_portal_configuration: str | None = None
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

    @field_validator(*BILLING_SETTINGS, "signing_key_id", mode="before")
    @classmethod
    def _blank_is_unset(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value.strip() if isinstance(value, str) else value

    @field_validator("migration_database_url", mode="before")
    @classmethod
    def _blank_url_is_unset(cls, value: object) -> object:
        return None if isinstance(value, str) and not value.strip() else value

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

    @field_validator("admin_url", mode="before")
    @classmethod
    def _site_address_or_empty(cls, value: object) -> object:
        if value is None or (isinstance(value, str) and not value.strip()):
            return ""
        if not isinstance(value, str):
            return value
        address = value.strip().rstrip("/")
        parts = urlsplit(address)
        if not address.startswith(WEB_SCHEMES) or not parts.netloc or parts.path or parts.query:
            raise ValueError("ADMIN_URL must be a web address with no path, such as https://admin.example.com")
        return address

    @field_validator("email_intake_domain", mode="before")
    @classmethod
    def _host_or_empty(cls, value: object) -> object:
        if value is None or (isinstance(value, str) and not value.strip()):
            return ""
        if not isinstance(value, str) or HOST_NAME.fullmatch(value.strip().lower()) is None:
            raise ValueError("EMAIL_INTAKE_DOMAIN must be a domain such as intake.example.com")
        return value.strip().lower()

    @field_validator("sentry_dsn", mode="before")
    @classmethod
    def _dsn_or_empty(cls, value: object) -> object:
        if value is None or (isinstance(value, str) and not value.strip()):
            return ""
        if not isinstance(value, str) or SENTRY_DSN.fullmatch(value.strip()) is None:
            raise ValueError("SENTRY_DSN must be the https DSN of a Sentry project")
        return value.strip()

    @model_validator(mode="after")
    def _admin_on_its_own_host(self) -> Self:
        if self.admin_url and site_host(self.admin_url) == site_host(self.app_url):
            raise ValueError("ADMIN_URL must name a different host from APP_URL")
        return self

    @model_validator(mode="after")
    def _no_demo_model_in_production(self) -> Self:
        if self.gemini_backend == "demo" and self.app_environment == "production":
            raise ValueError("GEMINI_BACKEND=demo is refused when APP_ENVIRONMENT is production")
        return self

    @property
    def migration_url(self) -> str:
        return self.migration_database_url or self.database_url

    @property
    def can_send_texts(self) -> bool:
        if self.app_environment == "development":
            return True
        required = TEXT_SETTINGS.get(self.sms_transport, ())
        return bool(required) and all(getattr(self, name) for name in required)

    def refuse_unready_signup(self) -> None:
        if self.app_environment == "production" and self.self_signup_enabled and not (self.baa_url and self.terms_url):
            raise SignupNotReady("SELF_SIGNUP_ENABLED needs BAA_URL and TERMS_URL when APP_ENVIRONMENT is production")


def site_host(address: str) -> str:
    return urlsplit(address).netloc.lower()


@lru_cache
def get_settings() -> Settings:
    return Settings()
