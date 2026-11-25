from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4

from app.adapters.email_senders import SesEmail, SmtpEmail
from app.adapters.message_errors import MessageNotSent, MessengerNotConfigured
from app.adapters.sms_senders import SnsSms, TwilioSms
from app.core.config import Settings

__all__ = ["MessageNotSent", "Messenger", "MessengerNotConfigured", "OutboxMessenger", "build_messenger"]


EMAIL_SENDERS: dict[str, Any] = {"smtp": SmtpEmail, "ses": SesEmail}
SMS_SENDERS: dict[str, Any] = {"twilio": TwilioSms, "sns": SnsSms}


class EmailSender(Protocol):
    async def email(self, to: str, *, subject: str, body: str) -> None: ...


class SmsSender(Protocol):
    async def sms(self, to: str, *, body: str) -> None: ...


class Messenger(EmailSender, SmsSender, Protocol):
    pass


@dataclass(frozen=True)
class SplitMessenger:
    email_sender: EmailSender
    sms_sender: SmsSender

    async def email(self, to: str, *, subject: str, body: str) -> None:
        await self.email_sender.email(to, subject=subject, body=body)

    async def sms(self, to: str, *, body: str) -> None:
        await self.sms_sender.sms(to, body=body)


class OutboxMessenger:
    def __init__(self, folder: Path) -> None:
        self._folder = folder

    async def email(self, to: str, *, subject: str, body: str) -> None:
        await asyncio.to_thread(self._write, f"To: {to}\nSubject: {subject}\n\n{body}\n")

    async def sms(self, to: str, *, body: str) -> None:
        await asyncio.to_thread(self._write, f"To: {to}\nSMS\n\n{body}\n")

    def _write(self, text: str) -> None:
        self._folder.mkdir(parents=True, exist_ok=True)
        name = f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%S%f')}-{uuid4().hex[:8]}.txt"
        (self._folder / name).write_text(text, encoding="utf-8")


def build_messenger(settings: Settings) -> Messenger:
    outbox = OutboxMessenger(Path(settings.mail_outbox_dir)) if settings.mail_outbox_dir else None
    email = _chosen(settings.email_transport, EMAIL_SENDERS, outbox, settings)
    sms = _chosen(settings.sms_transport, SMS_SENDERS, outbox, settings)
    return SplitMessenger(email, sms)


def _chosen(transport: str, senders: dict[str, Any], outbox: OutboxMessenger | None, settings: Settings) -> Any:
    if transport != "outbox":
        return senders[transport](settings)
    if outbox is None:
        raise MessengerNotConfigured("MAIL_OUTBOX_DIR is needed when a transport is outbox")
    return outbox
