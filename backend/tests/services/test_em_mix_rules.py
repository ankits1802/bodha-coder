from __future__ import annotations

import math

import pytest

from app.services.em_mix import family_mix

INTERNAL_MEDICINE = {"99211": 0.0, "99212": 0.05, "99213": 0.30, "99214": 0.55, "99215": 0.10}


def _levels(mix):
    return {
        row["code"]: (row["count"], row["share"], row["benchmark"], row["points"], row["direction"])
        for row in mix["levels"]
    }


def test_a_provider_billing_high_levels_is_an_outlier_by_points_and_chi_square():
    mix = family_mix("office_established", {"99213": 5, "99214": 20, "99215": 15}, INTERNAL_MEDICINE)

    assert _levels(mix) == {
        "99211": (0, 0.0, 0.0, 0.0, None),
        "99212": (0, 0.0, 0.05, -5.0, None),
        "99213": (5, 0.125, 0.3, -17.5, "below"),
        "99214": (20, 0.5, 0.55, -5.0, None),
        "99215": (15, 0.375, 0.1, 27.5, "above"),
    }
    assert mix["visits"] == 40
    assert mix["chi_square"] == pytest.approx(8.901, abs=1e-3)
    assert mix["degrees_of_freedom"] == 1
    assert mix["p_value"] == pytest.approx(math.erfc(math.sqrt((81 / 14 + 81 / 26) / 2)))
    assert (mix["outlier"], mix["reasons"], mix["lean"]) == (True, ["points", "chi_square"], "higher")


def test_a_provider_billing_low_levels_is_an_outlier_in_the_other_direction():
    mix = family_mix("office_established", {"99212": 6, "99213": 4}, INTERNAL_MEDICINE)

    levels = _levels(mix)
    assert (levels["99212"][3], levels["99212"][4]) == (55.0, "above")
    assert (levels["99214"][3], levels["99214"][4]) == (-55.0, "below")
    assert mix["chi_square"] is None
    assert (mix["outlier"], mix["reasons"], mix["lean"]) == (True, ["points"], "lower")


def test_a_handful_of_visits_is_never_called_an_outlier():
    mix = family_mix("office_established", {"99215": 9}, INTERNAL_MEDICINE)

    assert all(row["direction"] is None for row in mix["levels"])
    assert (mix["outlier"], mix["lean"]) == (False, None)


def test_without_a_benchmark_nothing_is_compared():
    mix = family_mix("office_established", {"99215": 40}, None)

    assert mix["has_benchmark"] is False
    assert all(row["benchmark"] is None and row["points"] is None for row in mix["levels"])
    assert (mix["chi_square"], mix["outlier"]) == (None, False)
