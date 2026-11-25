from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, field_validator, model_validator

from app.codes.mips_reporting_codes import attach_reporting_codes, restrict_to_scope
from app.codes.mips_scope import MipsScope

__all__ = [
    "MACRO_PLACEHOLDER",
    "MEASURE_STATUSES",
    "NO_MEASURE_IN_SCOPE",
    "EligibleMeasure",
    "MeasureStatus",
    "MIPSQualityMeasuresOutput",
    "MipsMeasure",
    "MipsReview",
    "MipsScopeRecord",
    "ReportingCode",
    "ReportingCodes",
    "empty_mips",
    "scope_allows_nothing",
    "scoped_mips",
]

NO_MEASURE_IN_SCOPE = (
    "MIPS: this practice's measure list names no current CMS quality measure, so no measure was checked."
)
MACRO_PLACEHOLDER = "[PLACEHOLDER:"

MeasureStatus = Literal["met", "missing", "not_applicable"]
MEASURE_STATUSES: tuple[MeasureStatus, ...] = ("met", "missing", "not_applicable")
_STATUS_SPELLINGS = {"not applicable": "not_applicable", "not-applicable": "not_applicable", "n/a": "not_applicable"}


def _measure_status(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    wanted = value.strip().lower()
    return _STATUS_SPELLINGS.get(wanted, wanted)


class EligibleMeasure(BaseModel):
    measureName: str
    mipsId: str
    eligibilityRationale: str
    macro: str
    exceptionExclusion: str | None = None
    status: MeasureStatus

    @field_validator("status", mode="before")
    @classmethod
    def _normalize_status(cls, value: Any) -> Any:
        return _measure_status(value)

    @model_validator(mode="after")
    def _met_only_when_nothing_is_left_to_fill(self) -> EligibleMeasure:
        if self.status == "met" and MACRO_PLACEHOLDER in self.macro:
            self.status = "missing"
        return self


class MIPSQualityMeasuresOutput(BaseModel):
    eligibleMeasures: list[EligibleMeasure]
    fallbackMessage: str | None = None


class ReportingCode(BaseModel):
    code: str
    role: Literal["met", "not-met", "exception", "exclusion"]
    meaning: str
    criterion: int | None = None
    source: str


class ReportingCodes(BaseModel):
    collectionType: str
    specifications: list[str]
    codes: list[ReportingCode]
    note: str | None = None


class MipsScopeRecord(BaseModel):
    source: str
    measureIds: list[str]
    omitted: int
    appliedAt: str


class MipsMeasure(EligibleMeasure):
    status: MeasureStatus | None = None
    reportingCodes: ReportingCodes | None = None
    reportingCodesWithheld: str | None = None
    addedByOrganization: bool = False
    specUrl: str | None = None
    nursingFacilityNote: str | None = None


class MipsReview(BaseModel):
    eligibleMeasures: list[MipsMeasure]
    fallbackMessage: str | None = None
    scope: MipsScopeRecord | None = None


def scope_allows_nothing(scope: MipsScope | None) -> bool:
    return scope is not None and not scope.measure_ids


def scoped_mips(answer: MIPSQualityMeasuresOutput, scope: MipsScope | None) -> MipsReview:
    with_codes = attach_reporting_codes(answer.model_dump(mode="json"))
    return MipsReview.model_validate(restrict_to_scope(with_codes, scope))


def empty_mips(scope: MipsScope | None) -> MipsReview:
    return scoped_mips(MIPSQualityMeasuresOutput(eligibleMeasures=[], fallbackMessage=NO_MEASURE_IN_SCOPE), scope)
