from __future__ import annotations

from app.core.config import get_settings
from app.core.errors import Conflict, Invalid
from app.models import Provider

__all__ = [
    "CHANNELS",
    "CONTACT_FIELDS",
    "EMAIL",
    "TEXT",
    "TEXTS_UNAVAILABLE",
    "contact_for",
    "require_channel",
    "usable_channel",
]

EMAIL = "email"
TEXT = "sms"
CONTACT_FIELDS = {EMAIL: "email", TEXT: "phone"}
CHANNELS = tuple(CONTACT_FIELDS)
TEXTS_UNAVAILABLE = "text messages are not available; send by email"


def contact_for(provider: Provider, channel: str) -> str | None:
    return getattr(provider, CONTACT_FIELDS[channel])


def require_channel(provider: Provider, channel: str) -> None:
    if channel == TEXT and not get_settings().can_send_texts:
        raise Conflict(TEXTS_UNAVAILABLE)
    if not contact_for(provider, channel):
        raise Invalid(f"{provider.name} has no {CONTACT_FIELDS[channel]} on file")


def usable_channel(preferred: str, *, name: str, email: str | None) -> str:
    if preferred != TEXT or get_settings().can_send_texts:
        return preferred
    if not email:
        raise Invalid(f"{name} has no email on file")
    return EMAIL
