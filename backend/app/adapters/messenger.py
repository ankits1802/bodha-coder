from __future__ import annotations

import asyncio
import smtplib
import ssl
from datetime import UTC, datetime
from email.message import EmailMessage
from pathlib import Path
from typing import Protocol
from uuid import uuid4

import httpx

from app.core.config import Settings
from app.core.errors import Unavailable

TWILIO_URL = "https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"


class MessengerNotConfigured(Unavailable):
    pass


class MessageNotSent(Unavailable):
    pass


class Messenger(Protocol):
    async def email(self, to: str, *, subject: str, body: str) -> None: ...

    async def sms(self, to: str, *, body: str) -> None: ...


class SmtpTwilioMessenger:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def email(self, to: str, *, subject: str, body: str) -> None:
        settings = self._settings
        if not settings.smtp_host:
            raise MessengerNotConfigured("email is not set up")
        message = EmailMessage()
        message["From"], message["To"], message["Subject"] = settings.mail_from, to, subject
        message.set_content(body)
        await asyncio.to_thread(self._send_email, message)

    def _send_email(self, message: EmailMessage) -> None:
        settings = self._settings
        context = ssl.create_default_context()
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        with smtplib.SMTP(settings.smtp_host or "", settings.smtp_port, timeout=20) as server:
            server.starttls(context=context)
            if settings.smtp_user:
                server.login(settings.smtp_user, settings.smtp_password or "")
            server.send_message(message)

    async def sms(self, to: str, *, body: str) -> None:
        settings = self._settings
        if not (settings.twilio_account_sid and settings.twilio_auth_token and settings.twilio_from):
            raise MessengerNotConfigured("text messages are not set up")
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                TWILIO_URL.format(sid=settings.twilio_account_sid),
                data={"To": to, "From": settings.twilio_from, "Body": body},
                auth=(settings.twilio_account_sid, settings.twilio_auth_token),
            )
        if response.status_code >= 400:
            raise MessageNotSent(f"the text message was not sent ({response.status_code})")


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
    if settings.mail_outbox_dir:
        return OutboxMessenger(Path(settings.mail_outbox_dir))
    return SmtpTwilioMessenger(settings)
