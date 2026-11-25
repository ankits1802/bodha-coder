from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from app.services.uploads import due_at


def test_a_note_is_due_two_days_after_the_practice_day_of_service_ends():
    assert due_at(date(2026, 11, 25), ZoneInfo("America/Chicago")) == datetime(2026, 11, 28, 6, tzinfo=UTC)


def test_the_due_time_follows_the_practice_time_zone():
    assert due_at(date(2026, 11, 25), ZoneInfo("America/New_York")) == datetime(2026, 11, 28, 5, tzinfo=UTC)
