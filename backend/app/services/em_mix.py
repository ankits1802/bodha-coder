from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.codes.em import em_position
from app.codes.em_benchmarks import BENCHMARK_FAMILIES, EmBenchmarks, benchmark_family
from app.core.chi_square import goodness_of_fit
from app.models import Note, Provider
from app.services.visit_levels import visit_codes

__all__ = ["CHI_SQUARE_MIN_VISITS", "MIN_FAMILY_VISITS", "POINTS_LIMIT", "P_LIMIT", "em_mix", "family_mix"]

POINTS_LIMIT = 15.0
P_LIMIT = 0.01
CHI_SQUARE_MIN_VISITS = 30
MIN_FAMILY_VISITS = 10
SHARE_DECIMALS = 4
POINT_DECIMALS = 1
STATISTIC_DECIMALS = 3
DATASET = "CMS Evaluation and Management (E/M) Codes by Specialty"


async def em_mix(
    db: AsyncSession, practice_id: str, benchmarks: EmBenchmarks, *, start: date, end: date
) -> dict[str, Any]:
    rows = (
        await db.execute(
            select(Note.id, Note.provider_id).where(
                Note.practice_id == practice_id, Note.service_date >= start, Note.service_date <= end
            )
        )
    ).all()
    codes = await visit_codes(db, [note_id for note_id, _ in rows])
    counts: dict[str, dict[str, dict[str, int]]] = {}
    for note_id, provider_id in rows:
        position = em_position(codes.get(note_id, ""))
        if position is None or position[0].id not in BENCHMARK_FAMILIES:
            continue
        levels = counts.setdefault(provider_id, {}).setdefault(position[0].id, {})
        levels[codes[note_id]] = levels.get(codes[note_id], 0) + 1
    providers = (await db.scalars(select(Provider).where(Provider.id.in_(list(counts))))).all()
    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "benchmark": {"dataset": DATASET, "year": benchmarks.year, "source_url": benchmarks.source_url},
        "providers": [
            _provider_mix(provider, counts[provider.id], benchmarks)
            for provider in sorted(providers, key=lambda item: item.name)
        ],
    }


def family_mix(family_id: str, counts: Mapping[str, int], shares: Mapping[str, float] | None) -> dict[str, Any]:
    family = benchmark_family(family_id)
    total = sum(counts.values())
    levels = _level_rows(family_id, counts, shares)
    fit = None
    if shares is not None and total >= CHI_SQUARE_MIN_VISITS:
        fit = goodness_of_fit(
            [counts.get(level.code, 0) for level in family.levels],
            [total * shares[level.code] for level in family.levels],
        )
    reasons = ["points"] if any(row["direction"] for row in levels) else []
    if fit is not None and fit.p_value < P_LIMIT:
        reasons.append("chi_square")
    return {
        "family": family_id,
        "label": family.label,
        "visits": total,
        "has_benchmark": shares is not None,
        "levels": levels,
        "chi_square": round(fit.statistic, STATISTIC_DECIMALS) if fit else None,
        "degrees_of_freedom": fit.degrees_of_freedom if fit else None,
        "p_value": fit.p_value if fit else None,
        "outlier": bool(reasons),
        "reasons": reasons,
        "lean": _lean(family_id, counts, shares) if reasons else None,
    }


def _provider_mix(provider: Provider, counts: Mapping[str, Mapping[str, int]], benchmarks: EmBenchmarks) -> dict:
    specialty = benchmarks.specialty_for(provider.specialty)
    families = [
        family_mix(family_id, counts[family_id], benchmarks.shares(specialty, family_id) if specialty else None)
        for family_id in BENCHMARK_FAMILIES
        if family_id in counts
    ]
    return {
        "id": provider.id,
        "name": provider.name,
        "specialty": provider.specialty,
        "cms_specialty": specialty,
        "visits": sum(family["visits"] for family in families),
        "families": families,
    }


def _level_rows(family_id: str, counts: Mapping[str, int], shares: Mapping[str, float] | None) -> list[dict]:
    total = sum(counts.values())
    rows = []
    for level in benchmark_family(family_id).levels:
        share = counts.get(level.code, 0) / total if total else 0.0
        expected = shares[level.code] if shares is not None else None
        difference = (share - expected) * 100 if expected is not None else None
        rows.append(
            {
                "code": level.code,
                "count": counts.get(level.code, 0),
                "share": round(share, SHARE_DECIMALS),
                "benchmark": round(expected, SHARE_DECIMALS) if expected is not None else None,
                "points": round(difference, POINT_DECIMALS) if difference is not None else None,
                "direction": _direction(difference) if total >= MIN_FAMILY_VISITS else None,
            }
        )
    return rows


def _direction(difference: float | None) -> str | None:
    if difference is None or abs(difference) <= POINTS_LIMIT:
        return None
    return "above" if difference > 0 else "below"


def _lean(family_id: str, counts: Mapping[str, int], shares: Mapping[str, float] | None) -> str | None:
    levels = benchmark_family(family_id).levels
    total = sum(counts.values())
    if shares is None or total == 0:
        return None
    seen = sum(index * counts.get(level.code, 0) for index, level in enumerate(levels)) / total
    expected = sum(index * shares[level.code] for index, level in enumerate(levels))
    if seen == expected:
        return None
    return "higher" if seen > expected else "lower"
