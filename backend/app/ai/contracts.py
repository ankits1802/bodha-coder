from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Annotated, Any, Literal, Protocol

from pydantic import BaseModel, Field, WithJsonSchema, field_validator

from app.ai.audit import AuditChecklistOutput
from app.ai.cdi import CDIGapScanOutput
from app.ai.hcc import HccReview
from app.ai.mips import MipsReview
from app.codes.mips_scope import MipsScope

Section = Literal["em", "diagnoses", "code_review", "cdi", "audit", "mips", "hcc"]
Setting = Literal["office", "nursing_facility", "inpatient", "emergency", "home", "telehealth"]
DiagnosisStatus = Literal["supported", "needs_specificity", "suspected", "unsupported"]
Verdict = Literal["keep", "lower", "raise", "replace", "remove"]
MdmLevel = Literal["Straightforward", "Low", "Moderate", "High"]


@dataclass(frozen=True)
class BilledCode:
    code: str
    type: Literal["CPT", "ICD-10"]
    modifiers: tuple[str, ...] = ()
    units: int = 1


@dataclass(frozen=True)
class ReviewInputs:
    sections: frozenset[Section]
    setting: Setting
    place_of_service: str
    visit_type: str
    service_date: date
    billed_codes: tuple[BilledCode, ...]
    note_text: str | None = None
    pdf: bytes | None = None
    mips_scope: MipsScope | None = None


@dataclass(frozen=True)
class ModelReply:
    text: str
    model: str
    input_tokens: int
    output_tokens: int
    temperature: float | None = None
    schema_applied: bool | None = None


@dataclass(frozen=True)
class ModelRequest:
    prompt: str
    schema: dict[str, Any] | None
    system: str | None


class ModelClient(Protocol):
    async def generate(
        self,
        prompt: str,
        *,
        schema: dict[str, Any] | None,
        pdf: bytes | None = None,
        system: str | None = None,
    ) -> ModelReply: ...


class MdmElement(BaseModel):
    level: MdmLevel
    reason: str = ""


class MdmElements(BaseModel):
    problems: MdmElement
    data: MdmElement
    risk: MdmElement


class ModifierSuggestion(BaseModel):
    modifier: str
    code: str = ""
    reason: str = ""
    evidence: list[str] = Field(default_factory=list)


class AddOnSuggestion(BaseModel):
    code: str
    name: str = ""
    units: int = 1
    reason: str = ""
    evidence: list[str] = Field(default_factory=list)


def _bare_codes_as(field: str, value: Any) -> Any:
    if not isinstance(value, list):
        return value
    return [{field: item} if isinstance(item, str) else item for item in value]


class EmReview(BaseModel):
    code: str
    basis: Literal["MDM", "Time"] = "MDM"
    mdm_level: MdmLevel | None = None
    mdm_elements: MdmElements | None = None
    time_minutes: int | None = None
    justification: str = ""
    evidence: list[str] = Field(default_factory=list)
    next_level_needs: list[str] = Field(default_factory=list)
    alternative_code: str | None = None
    alternative_reason: str | None = None
    modifiers: list[ModifierSuggestion] = Field(default_factory=list)
    add_on_codes: list[AddOnSuggestion] = Field(default_factory=list)

    @field_validator("modifiers", mode="before")
    @classmethod
    def _bare_modifiers(cls, value: Any) -> Any:
        return _bare_codes_as("modifier", value)

    @field_validator("add_on_codes", mode="before")
    @classmethod
    def _bare_add_ons(cls, value: Any) -> Any:
        return _bare_codes_as("code", value)


class DiagnosisFinding(BaseModel):
    name: str
    icd10: str
    status: DiagnosisStatus
    meat: str = ""
    evidence: list[str] = Field(default_factory=list)
    suggestion: str = ""


class CodeVerdict(BaseModel):
    code: str
    verdict: Verdict
    suggested_code: str | None = None
    reason: str
    evidence: list[str] = Field(default_factory=list)


class CodeReview(BaseModel):
    em_reason: str = ""
    items: list[CodeVerdict] = Field(default_factory=list)


class PatientFacts(BaseModel):
    name: str | None = None
    age: int | None = None
    sex: str | None = None
    birth_date: Annotated[date | None, WithJsonSchema({"anyOf": [{"type": "string"}, {"type": "null"}]})] = None


class ReviewReport(BaseModel):
    patient: PatientFacts = Field(default_factory=PatientFacts)
    extracted_text: str | None = None
    em: EmReview | None = None
    diagnoses: list[DiagnosisFinding] | None = None
    code_review: CodeReview | None = None
    cdi: CDIGapScanOutput | None = None
    audit: AuditChecklistOutput | None = None
    mips: MipsReview | None = None
    hcc: HccReview | None = None


@dataclass(frozen=True)
class ReviewOutcome:
    report: ReviewReport
    prompt_version: str
    replies: tuple[ModelReply, ...] = field(default_factory=tuple)
    failed_sections: frozenset[Section] = frozenset()
    requests: tuple[ModelRequest, ...] = field(default_factory=tuple)
