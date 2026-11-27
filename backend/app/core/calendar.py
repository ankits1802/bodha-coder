from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.core.errors import Invalid

MAX_ZONE_NAME = 64


def zone_named(name: str) -> ZoneInfo:
    if not name or len(name) > MAX_ZONE_NAME:
        raise Invalid("choose a time zone")
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError) as error:
        raise Invalid(f"{name} is not a time zone") from error


def day_bounds(day: date, zone: ZoneInfo) -> tuple[datetime, datetime]:
    start = datetime.combine(day, time.min, zone)
    end = datetime.combine(day + timedelta(days=1), time.min, zone)
    return start.astimezone(UTC), end.astimezone(UTC)


def today_in(zone: ZoneInfo) -> date:
    return datetime.now(zone).date()


def shift_years(day: date, years: int) -> date:
    try:
        return day.replace(year=day.year + years)
    except ValueError:
        return day.replace(year=day.year + years, day=28)
