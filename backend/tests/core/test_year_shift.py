from datetime import date

from app.core.calendar import shift_years


def test_a_year_shift_keeps_the_calendar_day():
    assert shift_years(date(2026, 11, 27), -6) == date(2020, 11, 27)
    assert shift_years(date(2099, 6, 30), 1) == date(2100, 6, 30)


def test_the_twenty_ninth_of_february_becomes_the_twenty_eighth_in_a_common_year():
    assert shift_years(date(2028, 2, 29), 1) == date(2029, 2, 28)
    assert shift_years(date(2028, 2, 29), -6) == date(2022, 2, 28)
    assert shift_years(date(2028, 2, 29), -4) == date(2024, 2, 29)
