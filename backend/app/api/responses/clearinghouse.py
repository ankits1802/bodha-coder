from typing import Literal

from app.api.responses.base import View
from app.models import ACK_OUTCOMES, AUTH_KINDS, ID_QUALIFIERS, PATIENT_SEXES, RELATIONSHIPS, TRANSPORTS, USAGES

__all__ = [
    "AckUpload",
    "Charge",
    "ChargeList",
    "ClaimColumn",
    "ClaimDetailsRecord",
    "ClaimDetailsSuggestion",
    "ClaimDetailsView",
    "ClaimFilePage",
    "ClaimFileRecord",
    "ClaimReason",
    "ClaimSent",
    "ClearinghouseConnectionView",
    "ClearinghouseSummary",
    "ClearinghouseView",
    "ConnectionCheck",
    "HostKey",
]

Transport = Literal[TRANSPORTS]
Usage = Literal[USAGES]
IdQualifier = Literal[ID_QUALIFIERS]
Relationship = Literal[RELATIONSHIPS]
PatientSex = Literal[PATIENT_SEXES]
ClaimStatusName = Literal["missing", "ready", "sending", "sent", "accepted", "rejected", "failed"]


class ClearinghouseConnectionView(View):
    id: str
    name: str
    transport: Transport
    usage: Usage
    sender_qualifier: IdQualifier
    sender_id: str
    receiver_qualifier: IdQualifier
    receiver_id: str
    receiver_name: str
    host: str | None
    port: int | None
    username: str | None
    auth_kind: Literal[AUTH_KINDS] | None
    secret_saved: bool
    host_key_sha256: str | None
    outbound_folder: str | None
    inbound_folder: str | None
    saved_at: str


class ClearinghouseView(View):
    connection: ClearinghouseConnectionView | None
    encryption_ready: bool


class ClearinghouseSummary(View):
    name: str
    transport: Transport
    usage: Usage


class HostKey(View):
    host_key_sha256: str


class ConnectionCheck(View):
    ok: bool


class Charge(View):
    code: str
    cents: int


class ChargeList(View):
    items: list[Charge]


class ClaimDetailsRecord(View):
    patient_last: str
    patient_first: str
    patient_birth_date: str
    patient_sex: PatientSex
    street: str
    street_2: str | None
    city: str
    state: str
    zip_code: str
    relationship: Relationship
    member_id: str
    group_number: str | None
    subscriber_last: str | None
    subscriber_first: str | None
    revision: int
    confirmed_at: str
    confirmed_by: str


class ClaimDetailsSuggestion(View):
    source: Literal["note", "earlier_claim"]
    patient_name: str | None = None
    patient_last: str | None = None
    patient_first: str | None = None
    patient_birth_date: str | None = None
    patient_sex: PatientSex | None = None
    street: str | None = None
    street_2: str | None = None
    city: str | None = None
    state: str | None = None
    zip_code: str | None = None
    relationship: Relationship | None = None
    member_id: str | None = None
    group_number: str | None = None
    subscriber_last: str | None = None
    subscriber_first: str | None = None


class ClaimDetailsView(View):
    details: ClaimDetailsRecord | None
    suggested: ClaimDetailsSuggestion | None


class ClaimReason(View):
    code: str
    text: str


class ClaimColumn(View):
    status: ClaimStatusName
    at: str | None
    reasons: list[ClaimReason]
    missing: list[str]


class ClaimSent(View):
    id: str
    claims: int
    outcome: Literal["delivered"]


class ClaimFileRecord(View):
    id: str
    at: str
    by: str
    delivery: Literal["sftp", "download"]
    usage: Usage
    control_number: int
    claims: int
    total_cents: int
    file_name: str
    sha256: str
    outcome: Literal["sending", "delivered", "failed", "downloaded"]
    error: str | None
    file_ack: Literal[ACK_OUTCOMES] | None
    accepted: int
    rejected: int


class ClaimFilePage(View):
    items: list[ClaimFileRecord]
    total: int
    offset: int
    page_size: int


class AckUpload(View):
    kind: Literal["999", "277CA", "duplicate"]
    accepted: int
    rejected: int
    pending: int
    unlinked: int
