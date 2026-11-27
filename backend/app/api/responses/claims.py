from typing import Annotated, Literal

from pydantic import Field

from app.api.responses.base import Omittable, PlanType, View
from app.codes.payer_rules import Rule, Severity

__all__ = [
    "AocEdit",
    "ClaimChecks",
    "ClaimEdit",
    "ClaimLinesExport",
    "ClaimPayer",
    "ExportedClaim",
    "ExportedDiagnosis",
    "ExportedLine",
    "MueEdit",
    "NcciCoverage",
    "PayerFlag",
    "PtpEdit",
]


class NcciCoverage(View):
    quarter: str
    covers: bool


class PtpEdit(View):
    kind: Literal["ptp"]
    column1: str
    column2: str
    modifier_allowed: bool
    bypassed_by: str | None


class MueEdit(View):
    kind: Literal["mue"]
    code: str
    units: int
    limit: int
    mai: int


class AocEdit(View):
    kind: Literal["aoc"]
    code: str
    primaries: list[str]


ClaimEdit = Annotated[PtpEdit | MueEdit | AocEdit, Field(discriminator="kind")]


class ClaimPayer(View):
    name: str
    plan_type: PlanType | None


class PayerFlag(View):
    rule: Rule
    severity: Severity
    codes: list[str]
    earlier: Omittable[str] = None


class ClaimChecks(View):
    ncci: NcciCoverage
    edits: list[ClaimEdit]
    payer: ClaimPayer | None
    payer_flags: list[PayerFlag]


class ExportedDiagnosis(View):
    pointer: str
    code: str


class ExportedLine(View):
    line: int
    procedure: str
    modifiers: list[str]
    units: int
    pointers: list[str]


class ExportedClaim(View):
    note_id: str
    patient_name: str | None
    service_date: str
    place_of_service: str
    rendering_npi: str | None
    rendering_taxonomy: str | None
    billing_npi: str | None
    diagnoses: list[ExportedDiagnosis]
    lines: list[ExportedLine]


class ClaimLinesExport(View):
    claims: list[ExportedClaim]
