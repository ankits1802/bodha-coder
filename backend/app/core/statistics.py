from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from app.core.chi_square import MIN_EXPECTED, chi_square_sf, pooled_cells

__all__ = ["Z_95", "ChiSquare", "Rate", "chi_square_homogeneity", "f1_score", "wilson"]

Z_95 = 1.959963984540054


@dataclass(frozen=True)
class Rate:
    successes: int
    trials: int
    value: float | None
    low: float | None
    high: float | None

    def as_json(self) -> dict[str, int | float | None]:
        return {
            "successes": self.successes,
            "trials": self.trials,
            "value": self.value,
            "low": self.low,
            "high": self.high,
        }


@dataclass(frozen=True)
class ChiSquare:
    statistic: float
    degrees_of_freedom: int
    p_value: float


def wilson(successes: int, trials: int, *, z: float = Z_95) -> Rate:
    if trials < 0 or not 0 <= successes <= trials:
        raise ValueError(f"{successes} successes out of {trials} trials is not a proportion")
    if trials == 0:
        return Rate(0, 0, None, None, None)
    share = successes / trials
    spread = z * z / trials
    centre = (share + spread / 2) / (1 + spread)
    half = z * math.sqrt(share * (1 - share) / trials + spread / (4 * trials)) / (1 + spread)
    return Rate(successes, trials, share, max(0.0, centre - half), min(1.0, centre + half))


def f1_score(precision: float | None, recall: float | None) -> float | None:
    if precision is None or recall is None:
        return None
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def chi_square_homogeneity(first: Sequence[int], second: Sequence[int]) -> ChiSquare | None:
    if len(first) != len(second):
        raise ValueError(f"{len(first)} levels in one period but {len(second)} in the other")
    if any(count < 0 for count in (*first, *second)):
        raise ValueError("counts are never negative")
    totals = (sum(first), sum(second))
    if 0 in totals:
        return None
    columns = _pooled_columns(first, second, totals)
    if len(columns) < 2:
        return None
    grand = sum(totals)
    statistic = 0.0
    for column in columns:
        for observed, row in zip(column, totals, strict=True):
            expected = row * sum(column) / grand
            statistic += (observed - expected) ** 2 / expected
    degrees = len(columns) - 1
    return ChiSquare(statistic, degrees, chi_square_sf(statistic, degrees))


def _pooled_columns(first: Sequence[int], second: Sequence[int], totals: tuple[int, int]) -> list[tuple[float, float]]:
    grand, smallest = sum(totals), min(totals)
    least_expected = [smallest * (a + b) / grand for a, b in zip(first, second, strict=True)]
    pooled_first = pooled_cells(first, least_expected, minimum=MIN_EXPECTED)
    pooled_second = pooled_cells(second, least_expected, minimum=MIN_EXPECTED)
    return [(a, b) for (a, _), (b, _) in zip(pooled_first, pooled_second, strict=True)]
