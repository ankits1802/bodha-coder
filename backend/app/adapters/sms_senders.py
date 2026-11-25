from __future__ import annotations

import asyncio
from typing import Any

import boto3
import httpx
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError

from app.adapters.message_errors import MessageNotSent, MessengerNotConfigured
from app.core.config import Settings

TWILIO_URL = "https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
TRANSACTIONAL = {"AWS.SNS.SMS.SMSType": {"DataType": "String", "StringValue": "Transactional"}}


class TwilioSms:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def sms(self, to: str, *, body: str) -> None:
        settings = self._settings
        if not (settings.twilio_account_sid and settings.twilio_auth_token and settings.twilio_from):
            raise MessengerNotConfigured("text messages are not set up")
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.post(
                    TWILIO_URL.format(sid=settings.twilio_account_sid),
                    data={"To": to, "From": settings.twilio_from, "Body": body},
                    auth=(settings.twilio_account_sid, settings.twilio_auth_token),
                )
        except httpx.HTTPError as error:
            raise MessageNotSent("the text message was not sent") from error
        if response.status_code >= 400:
            raise MessageNotSent(f"the text message was not sent ({response.status_code})")


class SnsSms:
    def __init__(self, settings: Settings, *, client: Any = None) -> None:
        self._client = client or boto3.client("sns", region_name=settings.aws_messaging_region)

    async def sms(self, to: str, *, body: str) -> None:
        await asyncio.to_thread(self._send, to, body)

    def _send(self, to: str, body: str) -> None:
        try:
            self._client.publish(PhoneNumber=to, Message=body, MessageAttributes=TRANSACTIONAL)
        except NoCredentialsError as error:
            raise MessengerNotConfigured("text messages are not set up") from error
        except ClientError as error:
            code = error.response.get("Error", {}).get("Code", "error")
            raise MessageNotSent(f"the text message was not sent ({code})") from error
        except BotoCoreError as error:
            raise MessageNotSent("the text message was not sent") from error
