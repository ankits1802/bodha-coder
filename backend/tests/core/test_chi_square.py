from __future__ import annotations

import math

import pytest

from app.core.chi_square import chi_square_sf, goodness_of_fit, pooled_cells

TABLE_99TH_PERCENTILE = {1: 6.635, 2: 9.210, 3: 11.345, 4: 13.277, 5: 15.086}


@pytest.mark.parametrize(("degrees", "critical"), sorted(TABLE_99TH_PERCENTILE.items()))
def test_the_upper_tail_matches_the_published_one_percent_critical_values(degrees, critical):
    assert chi_square_sf(critical, degrees) == pytest.approx(0.01, abs=1e-4)


def test_two_degrees_of_freedom_is_the_exponential_tail():
    assert chi_square_sf(4.0, 2) == pytest.approx(math.exp(-2.0))
    assert chi_square_sf(0.0, 3) == 1.0


def test_impossible_inputs_are_refused():
    with pytest.raises(ValueError, match="degrees of freedom"):
        chi_square_sf(1.0, 0)
    with pytest.raises(ValueError, match="never negative"):
        chi_square_sf(-1.0, 2)


def test_sparse_levels_are_pooled_with_their_neighbours():
    observed, expected = [0, 0, 5, 20, 15], [0, 2, 12, 22, 4]
    assert pooled_cells(observed, expected) == [(5, 14), (35, 26)]


def test_the_statistic_uses_the_pooled_cells():
    fit = goodness_of_fit([0, 0, 5, 20, 15], [0, 2, 12, 22, 4])
    assert fit is not None
    assert fit.degrees_of_freedom == 1
    assert fit.statistic == pytest.approx(81 / 14 + 81 / 26)
    assert fit.p_value == pytest.approx(math.erfc(math.sqrt((81 / 14 + 81 / 26) / 2)))


def test_one_pooled_cell_is_not_a_test():
    assert goodness_of_fit([3, 2], [2, 3]) is None
