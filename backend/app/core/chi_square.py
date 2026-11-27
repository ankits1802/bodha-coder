from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

__all__ = ["MIN_EXPECTED", "GoodnessOfFit", "chi_square_sf", "goodness_of_fit", "pooled_cells"]

MIN_EXPECTED = 5.0


@dataclass(frozen=True, slots=True)
class GoodnessOfFit:
    statistic: float
    degrees_of_freedom: int
    p_value: float


def chi_square_sf(statistic: float, degrees_of_freedom: int) -> float:
    if degrees_of_freedom < 1:
        raise ValueError(f"degrees of freedom must be at least 1, got {degrees_of_freedom}")
    if statistic < 0 or math.isnan(statistic):
        raise ValueError(f"a chi-square statistic is never negative, got {statistic}")
    if statistic == 0:
        return 1.0
    half = statistic / 2
    if degrees_of_freedom % 2 == 0:
        terms = (i * math.log(half) - math.lgamma(i + 1) for i in range(degrees_of_freedom // 2))
        return min(1.0, sum(math.exp(term - half) for term in terms))
    terms = ((i - 0.5) * math.log(half) - math.lgamma(i + 0.5) for i in range(1, (degrees_of_freedom + 1) // 2))
    return min(1.0, math.erfc(math.sqrt(half)) + sum(math.exp(term - half) for term in terms))


def pooled_cells(
    observed: Sequence[float], expected: Sequence[float], *, minimum: float = MIN_EXPECTED
) -> list[tuple[float, float]]:
    if len(observed) != len(expected):
        raise ValueError(f"{len(observed)} observed counts but {len(expected)} expected counts")
    cells: list[tuple[float, float]] = []
    seen, wanted = 0.0, 0.0
    for count, share in zip(observed, expected, strict=True):
        seen, wanted = seen + count, wanted + share
        if wanted >= minimum:
            cells.append((seen, wanted))
            seen, wanted = 0.0, 0.0
    if cells and (seen or wanted):
        last_seen, last_wanted = cells.pop()
        cells.append((last_seen + seen, last_wanted + wanted))
    return cells


def goodness_of_fit(observed: Sequence[float], expected: Sequence[float]) -> GoodnessOfFit | None:
    cells = pooled_cells(observed, expected)
    if len(cells) < 2:
        return None
    statistic = sum((seen - wanted) ** 2 / wanted for seen, wanted in cells)
    degrees = len(cells) - 1
    return GoodnessOfFit(statistic, degrees, chi_square_sf(statistic, degrees))
