from typing import Literal

from app.models import MESSAGE_OUTCOMES, REFUSAL_REASONS, SENDER_KINDS
from app.services.email_intake_files import ACCEPTED, REFUSED

from .view import View

__all__ = [
    "EmailIntakeView",
    "IntakeMessageFile",
    "IntakeMessagePage",
    "IntakeMessageRow",
    "IntakeSenderView",
    "IntakeTestView",
    "PreviousIntakeAddress",
]


class IntakeSenderView(View):
    id: str
    pattern: str
    kind: Literal[SENDER_KINDS]
    added_at: str


class PreviousIntakeAddress(View):
    address: str | None
    since: str
    until: str | None


class EmailIntakeView(View):
    available: bool
    address: str | None
    address_since: str | None
    previous: list[PreviousIntakeAddress]
    senders: list[IntakeSenderView]


class IntakeTestView(View):
    id: str
    sent_at: str
    arrived_at: str | None


class IntakeMessageFile(View):
    outcome: Literal[ACCEPTED, REFUSED]
    reason: str | None
    note_id: str | None


class IntakeMessageRow(View):
    id: str
    received_at: str
    sender: str | None
    outcome: Literal[MESSAGE_OUTCOMES]
    reason: Literal[REFUSAL_REASONS] | None
    accepted_files: int
    refused_files: int
    files: list[IntakeMessageFile]


class IntakeMessagePage(View):
    items: list[IntakeMessageRow]
    total: int
    offset: int
    page_size: int
