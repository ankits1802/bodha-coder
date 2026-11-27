import math

import pytest

from app.core.statistics import bootstrap_ratio, chi_square_homogeneity, f1_score, wilson

WILSON_BY_HAND = [
    (1, 1, 1.0, 0.206549, 1.0),
    (1, 2, 0.5, 0.094531, 0.905469),
    (0, 2, 0.0, 0.0, 0.65762),
    (27, 30, 0.9, 0.743789, 0.9654),
    (30, 30, 1.0, 0.886487, 1.0),
    (35, 35, 1.0, 0.901099, 1.0),
    (143, 150, 143 / 150, 0.906814, 0.977213),
    (142, 150, 142 / 150, 0.898296, 0.97273),
]


@pytest.mark.parametrize(("successes", "trials", "value", "low", "high"), WILSON_BY_HAND)
def test_wilson_intervals_match_the_roots_of_the_score_equation(successes, trials, value, low, high):
    rate = wilson(successes, trials)
    assert rate.value == pytest.approx(value)
    assert rate.low == pytest.approx(low, abs=1e-6)
    assert rate.high == pytest.approx(high, abs=1e-6)


def test_no_trials_is_not_estimable_and_impossible_counts_are_refused():
    assert wilson(0, 0).as_json() == {"successes": 0, "trials": 0, "value": None, "low": None, "high": None}
    with pytest.raises(ValueError, match="not a proportion"):
        wilson(3, 2)


def test_two_notes_give_the_range_of_their_own_ratios():
    rate = bootstrap_ratio([(3, 4), (4, 4)])
    assert (rate.successes, rate.trials, rate.value) == (7, 8, 0.875)
    assert (rate.low, rate.high) == (0.75, 1.0)


def test_one_note_has_no_spread():
    assert bootstrap_ratio([(2, 3)]).as_json() == {
        "successes": 2,
        "trials": 3,
        "value": pytest.approx(2 / 3),
        "low": pytest.approx(2 / 3),
        "high": pytest.approx(2 / 3),
    }


def test_the_bootstrap_interval_holds_the_estimate_and_narrows_with_more_notes():
    notes = [(3, 4), (4, 4), (1, 3), (5, 5), (2, 2), (0, 1), (3, 3), (2, 4)]
    few, many = bootstrap_ratio(notes), bootstrap_ratio(notes * 10)
    assert few.value == many.value == pytest.approx(20 / 26)
    for rate in (few, many):
        assert rate.low is not None and rate.high is not None
        assert rate.low <= rate.value <= rate.high
    assert many.high - many.low < few.high - few.low


def test_the_bootstrap_is_repeatable_and_refuses_impossible_counts():
    notes = [(3, 4), (4, 4), (1, 3), (5, 5)]
    assert bootstrap_ratio(notes) == bootstrap_ratio(notes)
    assert bootstrap_ratio([(0, 0), (0, 0)]).as_json() == {
        "successes": 0,
        "trials": 0,
        "value": None,
        "low": None,
        "high": None,
    }
    with pytest.raises(ValueError, match="part <= whole"):
        bootstrap_ratio([(5, 4)])


def test_f1_is_the_harmonic_mean_of_precision_and_recall():
    assert f1_score(8 / 9, 1.0) == pytest.approx(16 / 17)
    assert f1_score(0.0, 0.0) == 0.0
    assert f1_score(None, 1.0) is None


def test_two_periods_with_one_degree_of_freedom():
    test = chi_square_homogeneity([10, 20], [30, 30])
    assert test is not None
    assert (test.statistic, test.degrees_of_freedom) == (pytest.approx(2.25), 1)
    assert test.p_value == pytest.approx(math.erfc(math.sqrt(1.125)))


def test_three_levels_use_the_two_degree_exponential_tail():
    test = chi_square_homogeneity([5, 10, 15], [30, 20, 10])
    assert test is not None
    assert (test.statistic, test.degrees_of_freedom) == (pytest.approx(96 / 7), 2)
    assert test.p_value == pytest.approx(math.exp(-48 / 7))


def test_sparse_levels_are_pooled_with_the_next_level():
    test = chi_square_homogeneity([1, 2, 10, 20], [2, 1, 30, 30])
    assert test is not None
    assert (test.statistic, test.degrees_of_freedom) == (pytest.approx(1.4635799, abs=1e-6), 1)


def test_an_empty_period_has_no_test():
    assert chi_square_homogeneity([0, 0], [4, 9]) is None
    assert chi_square_homogeneity([3, 0], [4, 0]) is None
