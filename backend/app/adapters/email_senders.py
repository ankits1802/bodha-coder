from __future__ import annotations

import asyncio
import smtplib
import ssl
from email.message import EmailMessage
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError

from app.adapters.mail_layout import html_from_text
from app.adapters.message_errors import MessageNotSent, MessengerNotConfigured
from app.core.config import Settings


class SmtpEmail:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def email(self, to: str, *, subject: str, body: str) -> None:
        settings = self._settings
        if not settings.smtp_host:
            raise MessengerNotConfigured("email is not set up")
        message = EmailMessage()
        message["From"], message["To"], message["Subject"] = settings.mail_from, to, subject
        message.set_content(body)
        message.add_alternative(html_from_text(subject, body), subtype="html")
        await asyncio.to_thread(self._send, message)

    def _send(self, message: EmailMessage) -> None:
        settings = self._settings
        context = ssl.create_default_context()
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        try:
            with smtplib.SMTP(settings.smtp_host or "", settings.smtp_port, timeout=20) as server:
                server.starttls(context=context)
                if settings.smtp_user:
                    server.login(settings.smtp_user, settings.smtp_password or "")
                server.send_message(message)
        except (smtplib.SMTPException, OSError) as error:
            raise MessageNotSent("the email was not sent") from error


class SesEmail:
    def __init__(self, settings: Settings, *, client: Any = None) -> None:
        self._settings = settings
        self._client = client or boto3.client("sesv2", region_name=settings.aws_messaging_region)

    async def email(self, to: str, *, subject: str, body: str) -> None:
        request: dict[str, Any] = {
            "FromEmailAddress": self._settings.mail_from,
            "Destination": {"ToAddresses": [to]},
            "Content": {
                "Simple": {
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body": {
                        "Text": {"Data": body, "Charset": "UTF-8"},
                        "Html": {"Data": html_from_text(subject, body), "Charset": "UTF-8"},
                    },
                }
            },
        }
        if self._settings.ses_configuration_set:
            request["ConfigurationSetName"] = self._settings.ses_configuration_set
        await asyncio.to_thread(self._send, request)

    def _send(self, request: dict[str, Any]) -> None:
        try:
            self._client.send_email(**request)
        except NoCredentialsError as error:
            raise MessengerNotConfigured("email is not set up") from error
        except ClientError as error:
            code = error.response.get("Error", {}).get("Code", "error")
            raise MessageNotSent(f"the email was not sent ({code})") from error
        except BotoCoreError as error:
            raise MessageNotSent("the email was not sent") from error
