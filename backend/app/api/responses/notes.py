from typing import Any, Literal

from app.api.responses.base import Channel, Omittable, RequestStatus, TextSource, View
from app.api.responses.work import NoteSummary
from app.codes.billing_codes import CodeType
from app.codes.fees import RateSetting
from app.models import ANALYSIS_STATUSES, CHOICES, CODE_SET_KINDS, SUGGESTION_KINDS

__all__ = [
    "AddendumAnswer",
    "AddendumQuestion",
    "AddendumRequestView",
    "AnalysisRevision",
    "AnalysisView",
    "AuditOverview",
    "CdiOverview",
    "ClaimEstimate",
    "ClaimEstimates",
    "CmsCdiCompliance",
    "CodeJson",
    "CodeLinkingOpportunity",
    "CodeSetRevision",
    "CodingComplianceCheck",
    "DecisionRecord",
    "EstimateLine",
    "Finding",
    "FindingAction",
    "MipsScope",
    "NoteDetail",
    "NoteHeader",
    "NoteHistory",
    "NoteText",
    "PointerChoice",
    "ProviderRef",
    "RequiredElement",
    "TextRevision",
]

AnalysisStatus = Literal[ANALYSIS_STATUSES]
Choice = Literal[CHOICES]
FindingAction = Literal["keep", "lower", "raise", "replace", "add", "remove", "review", "ask", "info", "not_applicable"]


class ProviderRef(View):
    id: str
    name: str
    credential: str
    specialty: str | None
    channel: Channel


class NoteHeader(NoteSummary):
    assignee_name: str | None
    patient_age: int | None
    patient_sex: str | None
    provider: ProviderRef


class TextRevision(View):
    revision: int
    source: TextSource
    text: str


class NoteText(TextRevision):
    created_at: str


class CodeLinkingOpportunity(View):
    diagnosis: str
    relatedFindings: str
    suggestion: str


class CdiOverview(View):
    overallCDIScore: int | float | None
    summaryGuidance: str | None
    codeLinkingOpportunities: list[CodeLinkingOpportunity] | None


class RequiredElement(View):
    element: str
    present: bool
    location: str | None
    deficiency: str | None


class CodingComplianceCheck(View):
    check: str
    status: Literal["Pass", "Fail", "Warning"]
    finding: str


class CmsCdiCompliance(View):
    standard: str
    compliant: bool
    note: str


class AuditOverview(View):
    overallComplianceScore: int | float | None
    auditSummary: str | None
    requiredElements: list[RequiredElement] | None
    codingCompliance: list[CodingComplianceCheck] | None
    cmsCDICompliance: list[CmsCdiCompliance] | None


class MipsScope(View):
    source: str
    measureIds: list[str]
    omitted: int
    appliedAt: str


class AnalysisView(View):
    id: str
    revision: int
    status: AnalysisStatus
    model: str | None
    prompt_version: str | None
    finished_at: str | None
    failed_sections: list[str]
    cdi: CdiOverview
    audit: AuditOverview
    mips_scope: MipsScope | None


class Finding(View):
    kind: Literal[SUGGESTION_KINDS]
    key: str
    action: FindingAction
    title: str
    reasoning: str
    code_before: str | None
    code_after: str | None
    evidence: list[str]
    severity: str | None
    detail: dict[str, Any]
    default_choice: Choice
    choice: Choice
    allowed: list[Choice]


class EstimateLine(View):
    code: str
    amount: float | None


class ClaimEstimate(View):
    total: float
    lines: list[EstimateLine]
    unpriced: list[str]


class ClaimEstimates(View):
    release: str
    setting: RateSetting
    billed: ClaimEstimate
    claim: ClaimEstimate
    difference: float


class AnalysisRevision(View):
    revision: int
    reason: str
    status: AnalysisStatus
    model: str | None
    finished_at: str | None
    error: str | None


class CodeJson(View):
    code: str
    type: CodeType
    modifiers: list[str]
    units: Omittable[int] = None
    pointers: Omittable[list[str]] = None


class CodeSetRevision(View):
    kind: Literal[CODE_SET_KINDS]
    revision: int
    codes: list[CodeJson]
    reason: str
    by: str | None
    at: str


class PointerChoice(View):
    code: str
    diagnoses: list[str]


class DecisionRecord(View):
    key: str
    choice: Choice
    by: str | None
    at: str
    pointers: PointerChoice | None


class NoteHistory(View):
    analyses: list[AnalysisRevision]
    code_sets: list[CodeSetRevision]
    decisions: list[DecisionRecord]


class AddendumQuestion(View):
    key: str
    text: str
    context: list[str]
    options: list[str]


class AddendumAnswer(View):
    key: str
    choice: str
    comment: str | None


class AddendumRequestView(View):
    id: str
    status: RequestStatus
    channel: Channel
    questions: list[AddendumQuestion]
    answers: list[AddendumAnswer] | None
    addendum_text: str | None
    hold_claim: bool
    sent_at: str
    answered_at: str | None


class NoteDetail(View):
    note: NoteHeader
    failure: str | None
    texts: list[NoteText]
    analysis: AnalysisView | None
    findings: list[Finding]
    claim: list[str]
    estimate: ClaimEstimates | None
    history: NoteHistory
    requests: list[AddendumRequestView]
