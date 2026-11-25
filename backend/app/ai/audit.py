from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator
from pydantic.json_schema import SkipJsonSchema

from app.ai.choices import matched_choice
from app.ai.item_ids import stamp_ids
from app.ai.replacement_target import ReplacementTarget

__all__ = [
    "RISK_AREA_ID_PREFIX",
    "AuditChecklistOutput",
    "AuditFinding",
    "CMSCDICompliance",
    "CodingComplianceCheck",
    "RequiredElement",
    "RiskArea",
    "stamp_audit_ids",
]

RISK_AREA_ID_PREFIX = "risk-"
RISK_AREA_DEFAULT_SECTION = "plan"
DEFAULT_FINDING_SEVERITY = "Medium"

_STATUSES = ("Pass", "Fail", "Warning")
_SEVERITIES = ("Critical", "High", "Medium", "Low")


class RequiredElement(BaseModel):
    element: str
    present: bool
    location: str | None = None
    deficiency: str | None = None


class CodingComplianceCheck(BaseModel):
    check: str
    status: Literal["Pass", "Fail", "Warning"]
    finding: str = ""

    @field_validator("status", mode="before")
    @classmethod
    def _normalize_status(cls, value: Any) -> Any:
        return matched_choice(value, _STATUSES)


class CMSCDICompliance(BaseModel):
    standard: str
    compliant: bool
    note: str = ""


class RiskArea(ReplacementTarget):
    id: SkipJsonSchema[str] = ""
    risk: str
    severity: Literal["Critical", "High", "Medium", "Low"]
    recommendation: str = ""
    targetSection: str = ""
    suggestedText: str = ""

    @field_validator("severity", mode="before")
    @classmethod
    def _normalize_severity(cls, value: Any) -> Any:
        return matched_choice(value, _SEVERITIES)


class AuditFinding(ReplacementTarget):
    id: SkipJsonSchema[str] = ""
    severity: str = DEFAULT_FINDING_SEVERITY
    title: str = ""
    detail: str = ""
    targetSection: str = ""
    suggestedText: str = ""

    @field_validator("severity", mode="before")
    @classmethod
    def _normalize_severity(cls, value: Any) -> Any:
        snapped = matched_choice(value, _SEVERITIES)
        return snapped if isinstance(snapped, str) and snapped.strip() else DEFAULT_FINDING_SEVERITY


class AuditChecklistOutput(BaseModel):
    requiredElements: list[RequiredElement]
    codingCompliance: list[CodingComplianceCheck]
    cmsCDICompliance: list[CMSCDICompliance]
    riskAreas: list[RiskArea]
    overallComplianceScore: int | float
    auditSummary: str
    findings: list[AuditFinding] = Field(default_factory=list)


def stamp_audit_ids(audit: AuditChecklistOutput) -> AuditChecklistOutput:
    findings = stamp_ids(audit.findings, identity=lambda finding: finding.title)
    risks = stamp_ids(
        audit.riskAreas,
        identity=lambda risk: risk.risk,
        prefix=RISK_AREA_ID_PREFIX,
        default_section=RISK_AREA_DEFAULT_SECTION,
    )
    return audit.model_copy(update={"findings": findings, "riskAreas": risks})
