from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from app.codes.mips_scope import MipsScope
from app.codes.practice_measures import PracticeMeasureDefinition, practice_key_in_answer

__all__ = [
    "PRACTICE_CODE_SOURCE",
    "PRACTICE_COLLECTION",
    "PracticeMeasureMark",
    "split_practice_answers",
    "with_practice_measures",
]

PRACTICE_COLLECTION = "Practice measure"
PRACTICE_CODE_SOURCE = "practice"
_MEANINGS = {"met": "Reported when the measure is met", "not-met": "Reported when the measure is not met"}


class PracticeMeasureMark(BaseModel):
    key: str
    version: int
    identifier: str | None = None


def split_practice_answers(measures: list[Any]) -> tuple[list[Any], list[dict[str, Any]]]:
    cms: list[Any] = []
    practice: list[dict[str, Any]] = []
    for measure in measures:
        if isinstance(measure, dict) and practice_key_in_answer(measure.get("mipsId")) is not None:
            practice.append(measure)
        else:
            cms.append(measure)
    return cms, practice


def with_practice_measures(payload: dict[str, Any], answers: list[dict[str, Any]], scope: MipsScope | None) -> Any:
    record = payload.get("scope")
    if scope is None or not isinstance(record, dict):
        return payload
    kept = _kept_answers(answers, scope)
    record = {**record, "measureIds": list(scope.listed_ids), "omitted": record["omitted"] + len(answers) - len(kept)}
    return {**payload, "eligibleMeasures": [*payload["eligibleMeasures"], *kept], "scope": record}


def _kept_answers(answers: list[dict[str, Any]], scope: MipsScope) -> list[dict[str, Any]]:
    defined = {measure.key: measure for measure in scope.practice_measures}
    kept: dict[str, dict[str, Any]] = {}
    for answer in answers:
        key = practice_key_in_answer(answer.get("mipsId"))
        if key in defined and key not in kept:
            kept[key] = _entry(answer, defined[key])
    return list(kept.values())


def _entry(answer: dict[str, Any], definition: PracticeMeasureDefinition) -> dict[str, Any]:
    mark = PracticeMeasureMark(key=definition.key, version=definition.version, identifier=definition.identifier)
    return {
        **answer,
        "mipsId": definition.mips_id,
        "measureName": definition.name,
        "exceptionExclusion": None,
        "reportingCodes": _reporting_codes(definition),
        "reportingCodesWithheld": None,
        "addedByOrganization": False,
        "specUrl": None,
        "nursingFacilityNote": None,
        "practiceMeasure": mark.model_dump(),
    }


def _reporting_codes(definition: PracticeMeasureDefinition) -> dict[str, Any] | None:
    rows = [("met", code) for code in definition.met_codes] + [("not-met", code) for code in definition.not_met_codes]
    if not rows:
        return None
    return {
        "collectionType": PRACTICE_COLLECTION,
        "specifications": [],
        "codes": [
            {"code": code, "role": role, "meaning": _MEANINGS[role], "criterion": None, "source": PRACTICE_CODE_SOURCE}
            for role, code in rows
        ],
        "note": None,
    }
