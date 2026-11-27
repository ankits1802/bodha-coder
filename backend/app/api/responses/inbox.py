from typing import Literal

from app.api.responses.base import Omittable, View
from app.models import INBOX_KINDS, REQUEST_PURPOSES

__all__ = ["InboxCount", "InboxEntry", "InboxKind", "InboxPage", "InboxPayload"]

InboxKind = Literal[INBOX_KINDS]


class InboxPayload(View):
    questions: Omittable[int] = None
    purpose: Omittable[Literal[REQUEST_PURPOSES]] = None
    comment_id: Omittable[str] = None
    on: Omittable[Literal["finding", "note"]] = None
    run_id: Omittable[str] = None
    notes: Omittable[int] = None
    access_until: Omittable[str] = None
    ends_on: Omittable[str] = None
    reason: Omittable[str] = None


class InboxEntry(View):
    id: str
    kind: InboxKind
    note_id: str | None
    actor_name: str
    payload: InboxPayload
    patient_name: str | None
    service_date: str | None
    created_at: str
    read_at: str | None


class InboxPage(View):
    items: list[InboxEntry]
    total: int
    unread: int
    offset: int
    page_size: int


class InboxCount(View):
    unread: int
