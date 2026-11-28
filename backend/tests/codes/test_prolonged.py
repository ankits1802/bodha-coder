import pytest

from app.codes.billing_codes import is_known_cpt, parse_code_list
from app.codes.prolonged import VisitTime, prolonged_problem, prolonged_units, prolonged_units_due


@pytest.mark.parametrize(
    ("visit", "minutes", "units"),
    [
        ("99205", 74, 0),
        ("99205", 75, 1),
        ("99205", 89, 1),
        ("99205", 90, 2),
        ("99205", 104, 2),
        ("99205", 105, 3),
        ("99215", 54, 0),
        ("99215", 55, 1),
        ("99215", 69, 1),
        ("99215", 70, 2),
        ("99215", 85, 3),
        ("99214", 90, 0),
        ("99245", 90, 0),
        (None, 90, 0),
        ("99215", None, 0),
    ],
)
def test_99417_starts_at_75_minutes_with_99205_and_55_with_99215_then_every_full_15(visit, minutes, units):
    assert prolonged_units("99417", visit, minutes) == units


@pytest.mark.parametrize(
    ("visit", "minutes", "units"),
    [("99205", 88, 0), ("99205", 89, 1), ("99205", 103, 1), ("99205", 104, 2), ("99215", 69, 1), ("99214", 90, 0)],
)
def test_medicare_g2212_starts_at_89_and_69_minutes(visit, minutes, units):
    assert prolonged_units("G2212", visit, minutes) == units


def test_99417_is_a_code_bodha_accepts_although_medicare_does_not_pay_it():
    assert is_known_cpt("99417")
    assert is_known_cpt("G2212")
    parsed = parse_code_list("99215, 99417x2, I10")
    assert parsed.invalid == ()
    assert [(code.code, code.units) for code in parsed.codes] == [("99215", 1), ("99417", 2), ("I10", 1)]


def test_only_a_level_chosen_by_time_earns_prolonged_units():
    assert prolonged_units_due("99417", VisitTime("99215", True, 70)) == 2
    assert prolonged_units_due("99417", VisitTime("99215", False, 70)) == 0


def test_a_supported_prolonged_service_has_no_problem():
    assert prolonged_problem("99417", 2, VisitTime("99215", True, 70)) is None
    assert prolonged_problem("99417", 1, VisitTime("99205", True, 75)) is None
    assert prolonged_problem("G2212", 1, VisitTime("99215", True, 72)) is None


@pytest.mark.parametrize("visit", ["99214", "99204", "99245", "99350", None])
def test_99417_goes_only_with_99205_or_99215(visit):
    problem = prolonged_problem("99417", 1, VisitTime(visit, True, 120))
    assert problem is not None and problem.startswith("99417 is reported only with 99205 or 99215")


def test_99417_is_never_reported_with_a_level_set_by_medical_decision_making():
    problem = prolonged_problem("99417", 1, VisitTime("99215", False, 70))
    assert problem == "99417 needs a visit level chosen by documented total time, not by medical decision making."
    assert prolonged_problem("99417", 1, VisitTime("99215", True, None)) == problem


def test_time_short_of_the_first_unit_is_named():
    assert prolonged_problem("99417", 1, VisitTime("99215", True, 54)) == (
        "54 minutes is short of the 55 minutes 99417 needs with 99215."
    )
    assert prolonged_problem("G2212", 1, VisitTime("99215", True, 60)) == (
        "60 minutes is short of the 69 minutes G2212 needs with 99215."
    )


def test_units_must_match_the_full_15_minute_periods():
    assert prolonged_problem("99417", 1, VisitTime("99215", True, 70)) == (
        "70 minutes with 99215 is 2 units of 99417, not 1."
    )
    assert prolonged_problem("99417", 3, VisitTime("99205", True, 89)) == (
        "89 minutes with 99205 is 1 unit of 99417, not 3."
    )


def test_a_code_that_is_not_prolonged_service_is_refused():
    with pytest.raises(ValueError, match="99214 is not a prolonged service code"):
        prolonged_problem("99214", 1, VisitTime("99215", True, 70))
