from typing import Literal

from pydantic import Field

from app.api.responses.base import Lane, NoteStatus, View
from app.services.day_checks import CLONED_TEXT, HIGH_LEVEL_SHARE, TIME_OVER_DAY

__all__ = ["DayDuplicate", "DayLevelCount", "DayNote", "DayProvider", "FlaggedDays", "NoteDay", "ProviderDay"]


class DayProvider(View):
    id: str
    name: str


class DayNote(View):
    id: str
    patient_name: str | None
    status: NoteStatus
    lane: Lane | None
    em_code: str | None
    minutes: int | None


class DayLevelCount(View):
    code: str
    count: int


class DayDuplicate(View):
    first: str
    second: str
    similarity: float


class ProviderDay(View):
    provider: DayProvider
    service_date: str
    notes: list[DayNote]
    total_minutes: int
    timed_notes: int
    visits: int
    levels: list[DayLevelCount]
    high_level_visits: int
    high_level_share: float | None
    compared: int
    duplicates: list[DayDuplicate]
    flags: list[Literal[TIME_OVER_DAY, CLONED_TEXT, HIGH_LEVEL_SHARE]]


class NoteDay(ProviderDay):
    note_id: str


class FlaggedDays(View):
    start: str = Field(alias="from")
    end: str = Field(alias="to")
    days: list[ProviderDay]
