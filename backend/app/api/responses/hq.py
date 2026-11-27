from typing import Literal

from app.api.responses.base import View
from app.api.responses.team import MemberStatus
from app.services.hq import PLANS, STATUSES

__all__ = [
    "AdminLinkSent",
    "DemoRequestRow",
    "HqActivityEntry",
    "HqActivityPage",
    "HqOverview",
    "HqPlace",
    "HqPractice",
    "Renewal",
]


class HqOverview(View):
    practices: int
    people: int
    read_last_24h: int
    tokens_last_24h: int
    failed_last_24h: int
    waiting: int
    running: int


class HqPractice(View):
    id: str
    name: str
    status: Literal[STATUSES]
    plan: Literal[PLANS]
    seats: int
    users: int
    providers: int
    waiting: int
    renews_on: str | None
    time_zone: str
    failed_24h: int
    last_failure: str | None
    admin_name: str | None
    admin_email: str | None
    admin_status: MemberStatus | None


class AdminLinkSent(View):
    sent: Literal["invite", "reset"]


class Renewal(View):
    renews_on: str


class HqPlace(View):
    code: str
    name: str
    active: bool


class HqActivityEntry(View):
    at: str
    actor: str
    action: str
    practice_id: str | None
    detail: str | None


class HqActivityPage(View):
    items: list[HqActivityEntry]
    total: int
    offset: int
    page_size: int
    actions: list[str]


class DemoRequestRow(View):
    id: str
    name: str
    email: str
    organization: str
    message: str | None
    received_at: str
