from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import Field

from app.api.bodies import Body
from app.models import AUTH_KINDS, ID_QUALIFIERS, PATIENT_SEXES, RELATIONSHIPS, TRANSPORTS, USAGES
from app.services.charge_schedule import MAX_CHARGE_CENTS

__all__ = ["ChargeBody", "ClaimDetailsBody", "ClaimSendBody", "ConnectionBody", "HostKeyBody"]

INTERCHANGE_ID = r"^[A-Za-z0-9-]{1,15}$"
FINGERPRINT = r"^SHA256:[A-Za-z0-9+/]{43}$"
SEND_LIMIT = 500


class ConnectionBody(Body):
    name: str = Field(min_length=1, max_length=80)
    transport: Literal[TRANSPORTS]
    usage: Literal[USAGES]
    sender_qualifier: Literal[ID_QUALIFIERS] = "ZZ"
    sender_id: str = Field(pattern=INTERCHANGE_ID)
    receiver_qualifier: Literal[ID_QUALIFIERS] = "ZZ"
    receiver_id: str = Field(pattern=INTERCHANGE_ID)
    receiver_name: str = Field(min_length=1, max_length=60, pattern=r"^[A-Za-z0-9 &'(),./-]+$")
    host: str | None = Field(default=None, max_length=253)
    port: int | None = Field(default=None, ge=1, le=65535)
    username: str | None = Field(default=None, max_length=128)
    auth_kind: Literal[AUTH_KINDS] | None = None
    password: str | None = Field(default=None, max_length=256)
    private_key: str | None = Field(default=None, max_length=20_000)
    host_key_sha256: str | None = Field(default=None, pattern=FINGERPRINT)
    outbound_folder: str | None = Field(default=None, max_length=255)
    inbound_folder: str | None = Field(default=None, max_length=255)


class HostKeyBody(Body):
    host: str = Field(min_length=1, max_length=253)
    port: int = Field(default=22, ge=1, le=65535)


class ChargeBody(Body):
    cents: int = Field(ge=1, le=MAX_CHARGE_CENTS)


class ClaimDetailsBody(Body):
    patient_last: str = Field(min_length=1, max_length=60)
    patient_first: str = Field(min_length=1, max_length=35)
    patient_birth_date: date
    patient_sex: Literal[PATIENT_SEXES]
    street: str = Field(min_length=1, max_length=55)
    street_2: str | None = Field(default=None, max_length=55)
    city: str = Field(min_length=1, max_length=30)
    state: str = Field(min_length=2, max_length=2)
    zip_code: str = Field(min_length=5, max_length=10)
    relationship: Literal[RELATIONSHIPS]
    member_id: str = Field(min_length=2, max_length=80)
    group_number: str | None = Field(default=None, max_length=50)
    subscriber_last: str | None = Field(default=None, max_length=60)
    subscriber_first: str | None = Field(default=None, max_length=35)


class ClaimSendBody(Body):
    note_ids: list[str] | None = Field(default=None, max_length=SEND_LIMIT)
