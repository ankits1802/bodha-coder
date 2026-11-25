from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

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
    google_client_secret: str | None = None
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

    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.8-flash"
    gemini_timeout_seconds: int = 90
    ai_workers: int = 8
    ai_job_timeout_seconds: int = 600
    ai_max_attempts: int = 3
    ai_poll_seconds: float = 2.0

    email_transport: Literal["smtp", "ses", "outbox"] = "smtp"
    sms_transport: Literal["twilio", "sns", "outbox"] = "twilio"
    mail_from: str = "Bodha Coder <no-reply@bodha.health>"
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

    turnaround_hours: int = 48
    addendum_link_hours: int = 72
    provider_session_minutes: int = 30


@lru_cache
def get_settings() -> Settings:
    return Settings()
