from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from app.codes.billing_codes import Code
from app.codes.em import compare_em, em_position, is_em_code
from app.codes.icd import format_icd
from app.core.statistics import f1_score, wilson

__all__ = [
    "TIMED_LEVEL",
    "ClaimElements",
    "compare_elements",
    "elements_from_json",
    "elements_of",
    "em_direction",
    "em_level",
    "summarize",
]

TIMED_LEVEL = "Time"
DIRECTIONS = {
    "keep": "match",
    "lower": "higher",
    "raise": "lower",
    "replace": "family",
    "add": "absent",
    "not_applicable": "absent",
}
OTHER_DIRECTIONS = ("family", "absent")


@dataclass(frozen=True)
class ClaimElements:
    em: str | None
    icd: frozenset[str]
    modifiers: frozenset[str]

    def as_json(self) -> dict[str, Any]:
        return {"em": self.em, "icd": sorted(self.icd), "modifiers": sorted(self.modifiers)}


def elements_of(codes: Iterable[Code]) -> ClaimElements:
    listed = list(codes)
    em = next((code.code for code in listed if code.type == "CPT" and is_em_code(code.code)), None)
    icd = frozenset(format_icd(code.code) for code in listed if code.type == "ICD-10")
    modifiers = frozenset(modifier for code in listed if code.type == "CPT" for modifier in code.modifiers)
    return ClaimElements(em, icd, modifiers)


def elements_from_json(value: Mapping[str, Any]) -> ClaimElements:
    em = str(value.get("em") or "").strip().upper() or None
    icd = frozenset(format_icd(str(code)) for code in value.get("icd") or ())
    modifiers = frozenset(str(modifier).strip().upper() for modifier in value.get("modifiers") or ())
    return ClaimElements(em, icd, modifiers)


def em_level(code: str | None) -> str | None:
    position = em_position(code) if code else None
    if position is None:
        return None
    family, index = position
    return family.levels[index].mdm or TIMED_LEVEL


def em_direction(reference: str | None, compared: str | None) -> str:
    if reference == compared:
        return "match"
    if reference is None or compared is None:
        return "absent"
    return DIRECTIONS[compare_em(compared, reference).direction]


def compare_elements(reference: ClaimElements, compared: ClaimElements) -> dict[str, Any]:
    return {
        "em": {
            "reference": reference.em,
            "compared": compared.em,
            "match": reference.em == compared.em,
            "direction": em_direction(reference.em, compared.em),
        },
        "icd": {
            "matched": len(reference.icd & compared.icd),
            "compared": len(compared.icd),
            "reference": len(reference.icd),
            "missing": sorted(reference.icd - compared.icd),
            "extra": sorted(compared.icd - reference.icd),
            "match": reference.icd == compared.icd,
        },
        "modifiers": {
            "reference": sorted(reference.modifiers),
            "compared": sorted(compared.modifiers),
            "match": reference.modifiers == compared.modifiers,
        },
    }


def summarize(comparisons: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    total = len(comparisons)
    visits = [item["em"] for item in comparisons]
    diagnoses = [item["icd"] for item in comparisons]
    matched = sum(item["matched"] for item in diagnoses)
    precision = wilson(matched, sum(item["compared"] for item in diagnoses))
    recall = wilson(matched, sum(item["reference"] for item in diagnoses))
    return {
        "notes": total,
        "em": wilson(sum(item["match"] for item in visits), total).as_json(),
        "em_higher": wilson(sum(item["direction"] == "higher" for item in visits), total).as_json(),
        "em_lower": wilson(sum(item["direction"] == "lower" for item in visits), total).as_json(),
        "em_other": sum(item["direction"] in OTHER_DIRECTIONS for item in visits),
        "icd_precision": precision.as_json(),
        "icd_recall": recall.as_json(),
        "icd_f1": f1_score(precision.value, recall.value),
        "icd_exact": wilson(sum(item["match"] for item in diagnoses), total).as_json(),
        "modifiers": wilson(sum(item["modifiers"]["match"] for item in comparisons), total).as_json(),
    }
