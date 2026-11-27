import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_a_settings_error_never_echoes_the_values_it_was_given(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://bodha_app:hunter2-in-the-url@db:5432/bodha")
    monkeypatch.setenv("SECRET_KEY", "a-key-that-is-too-brief")
    monkeypatch.delenv("S3_BUCKET", raising=False)
    with pytest.raises(ValidationError) as caught:
        Settings(_env_file=None)
    message = str(caught.value)
    assert "s3_bucket" in message
    assert "hunter2-in-the-url" not in message
    assert "a-key-that-is-too-brief" not in message
