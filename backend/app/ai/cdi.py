from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, computed_field, field_validator
from pydantic.json_schema import SkipJsonSchema

from app.ai.choices import matched_choice
from app.ai.item_ids import stamp_ids
from app.ai.replacement_target import ReplacementTarget

__all__ = [
    "MAX_QUERY_OPTIONS",
    "QUERY_RECOMMENDATION_ID_PREFIX",
    "SPECIFICITY_GAP_ID_PREFIX",
    "UNDETERMINED_OPTION",
    "CDIGapScanOutput",
    "CodeLinkingOpportunity",
    "QueryRecommendation",
    "SpecificityGap",
    "stamp_cdi_ids",
    "with_undetermined_option",
]

SPECIFICITY_GAP_ID_PREFIX = "cdigap-"
QUERY_RECOMMENDATION_ID_PREFIX = "cdiq-"
CDI_DEFAULT_SECTION = "assessment"
UNDETERMINED_OPTION = "Clinically undetermined"
MAX_QUERY_OPTIONS = 4

_PRIORITIES = ("High", "Medium", "Low")


class SpecificityGap(ReplacementTarget):
    id: SkipJsonSchema[str] = ""
    finding: str
    currentDocumentation: str = ""
    recommendation: str = ""
    rationale: str = ""
    priority: Literal["High", "Medium", "Low"]
    targetSection: str = ""
    suggestedText: str = ""

    @field_validator("priority", mode="before")
    @classmethod
    def _normalize_priority(cls, value: Any) -> Any:
        if isinstance(value, str) and value.strip().lower() == "critical":
            return "High"
        return matched_choice(value, _PRIORITIES)


class CodeLinkingOpportunity(BaseModel):
    diagnosis: str
    relatedFindings: str
    suggestion: str


class QueryRecommendation(BaseModel):
    id: SkipJsonSchema[str] = ""
    query: str
    reason: str
    options: list[str]
    evidence: list[str] = Field(default_factory=list)
    targetSection: str = ""

    @computed_field
    @property
    def suggestedText(self) -> str:
        return ""

    @field_validator("options")
    @classmethod
    def _ends_with_undetermined(cls, value: list[str]) -> list[str]:
        return with_undetermined_option(value)


class CDIGapScanOutput(BaseModel):
    specificityGaps: list[SpecificityGap]
    codeLinkingOpportunities: list[CodeLinkingOpportunity]
    queryRecommendations: list[QueryRecommendation]
    overallCDIScore: int | float
    summaryGuidance: str


def with_undetermined_option(options: list[str]) -> list[str]:
    choices: list[str] = []
    for option in options:
        text = option.strip()
        if text and "undetermined" not in text.casefold() and text not in choices:
            choices.append(text)
    return [*choices[: MAX_QUERY_OPTIONS - 1], UNDETERMINED_OPTION]


def stamp_cdi_ids(scan: CDIGapScanOutput) -> CDIGapScanOutput:
    gaps = stamp_ids(
        scan.specificityGaps,
        identity=lambda gap: gap.finding,
        prefix=SPECIFICITY_GAP_ID_PREFIX,
        default_section=CDI_DEFAULT_SECTION,
    )
    queries = stamp_ids(
        scan.queryRecommendations,
        identity=lambda query: query.query,
        prefix=QUERY_RECOMMENDATION_ID_PREFIX,
        default_section=CDI_DEFAULT_SECTION,
    )
    return scan.model_copy(update={"specificityGaps": gaps, "queryRecommendations": queries})
