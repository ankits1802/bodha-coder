from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from app.codes.billing_codes import Code
from app.codes.em import is_em_code
from app.codes.payer_rules import COMPLEXITY_ADD_ON
from app.codes.prolonged import PROLONGED_CODES
from app.core.statistics import wilson

__all__ = [
    "LINE_METRICS",
    "SCORED_ADD_ONS",
    "ClaimLines",
    "compare_lines",
    "lines_from_expected",
    "lines_of",
    "summarize_lines",
]

SCORED_ADD_ONS = frozenset({COMPLEXITY_ADD_ON, *PROLONGED_CODES})
LINE_METRICS = ("procedures", "add_ons", "units", "place_of_service")


@dataclass(frozen=True)
class ClaimLines:
    procedures: frozenset[str]
    add_ons: frozenset[str]
    units: Mapping[str, int]
    place_of_service: str | None

    def as_json(self) -> dict[str, Any]:
        return {
            "procedures": sorted(self.procedures),
            "add_ons": sorted(self.add_ons),
            "units": dict(sorted(self.units.items())),
            "place_of_service": self.place_of_service,
        }


def lines_of(codes: Iterable[Code], place_of_service: str | None) -> ClaimLines:
    lines = [code for code in codes if code.type == "CPT" and not is_em_code(code.code)]
    units: dict[str, int] = {}
    for line in lines:
        units[line.code] = units.get(line.code, 0) + line.units
    return ClaimLines(
        frozenset(line.code for line in lines if line.code not in SCORED_ADD_ONS),
        frozenset(line.code for line in lines if line.code in SCORED_ADD_ONS),
        MappingProxyType(units),
        place_of_service,
    )


def lines_from_expected(expected: Mapping[str, Any], place_of_service: str) -> ClaimLines | None:
    claim = expected.get("claim")
    if not isinstance(claim, list):
        return None
    recorded = expected.get("place_of_service")
    return lines_of((Code.from_json(item) for item in claim), str(recorded) if recorded else place_of_service)


def compare_lines(reference: ClaimLines, compared: ClaimLines) -> dict[str, Any]:
    return {
        "procedures": _set_comparison(reference.procedures, compared.procedures),
        "add_ons": _set_comparison(reference.add_ons, compared.add_ons),
        "units": _units_comparison(reference.units, compared.units),
        "place_of_service": {
            "reference": reference.place_of_service,
            "compared": compared.place_of_service,
            "match": reference.place_of_service == compared.place_of_service,
            "scored": reference.place_of_service is not None,
        },
    }


def summarize_lines(comparisons: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    rates = {}
    for metric in LINE_METRICS:
        scored = [item[metric] for item in comparisons if item[metric]["scored"]]
        rates[metric] = wilson(sum(item["match"] for item in scored), len(scored)).as_json()
    return rates


def _set_comparison(reference: frozenset[str], compared: frozenset[str]) -> dict[str, Any]:
    return {
        "reference": sorted(reference),
        "compared": sorted(compared),
        "match": reference == compared,
        "scored": bool(reference or compared),
    }


def _units_comparison(reference: Mapping[str, int], compared: Mapping[str, int]) -> dict[str, Any]:
    shared = sorted(reference.keys() & compared.keys())
    return {
        "reference": {code: reference[code] for code in shared},
        "compared": {code: compared[code] for code in shared},
        "differing": [code for code in shared if reference[code] != compared[code]],
        "match": all(reference[code] == compared[code] for code in shared),
        "scored": bool(shared),
    }
