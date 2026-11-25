from __future__ import annotations

import asyncio
import smtplib
import ssl
from email.message import EmailMessage
from typing import Protocol

import httpx

from app.core.config import Settings

TWILIO_URL = "https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"


class MessengerNotConfigured(RuntimeError):
    pass


class MessageNotSent(RuntimeError):
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
            raise MessengerNotConfigured("SMTP_HOST is not set")
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
            raise MessengerNotConfigured("Twilio is not configured")
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                TWILIO_URL.format(sid=settings.twilio_account_sid),
                data={"To": to, "From": settings.twilio_from, "Body": body},
                auth=(settings.twilio_account_sid, settings.twilio_auth_token),
            )
        if response.status_code >= 400:
            raise MessageNotSent(f"SMS provider answered {response.status_code}")
