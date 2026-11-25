from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import pytest

from app.core.calendar import day_bounds, zone_named
from app.core.errors import Invalid

CHICAGO = ZoneInfo("America/Chicago")


def test_a_central_standard_time_day_runs_from_six_to_six_utc():
    assert day_bounds(date(2026, 11, 25), CHICAGO) == (
        datetime(2026, 11, 25, 6, tzinfo=UTC),
        datetime(2026, 11, 26, 6, tzinfo=UTC),
    )


def test_the_day_daylight_saving_ends_lasts_twenty_five_hours():
    start, end = day_bounds(date(2026, 11, 1), CHICAGO)
    assert (start, end) == (datetime(2026, 11, 1, 5, tzinfo=UTC), datetime(2026, 11, 2, 6, tzinfo=UTC))
    assert (end - start).total_seconds() == 25 * 3600


@pytest.mark.parametrize("name", ["", "Mars/Olympus_Mons", "../etc/passwd", "x" * 65])
def test_names_that_are_not_time_zones_are_refused(name):
    with pytest.raises(Invalid):
        zone_named(name)
