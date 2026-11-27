from typing import Literal

from app.api.responses.base import Role, View

__all__ = [
    "AgreementSides",
    "AgreementSummary",
    "AutonomyEligibility",
    "ClaimElements",
    "ComparisonSides",
    "ElementComparison",
    "EmComparison",
    "IcdComparison",
    "LevelMix",
    "LevelMixCount",
    "LevelMixTest",
    "LevelMixWindow",
    "ModifierComparison",
    "OptionProvider",
    "OptionReviewer",
    "ProviderAgreement",
    "ProviderAutonomy",
    "ProviderAutonomyList",
    "QualityOptions",
    "Rate",
    "SampleItemRow",
    "SampleList",
    "SampleOverview",
    "SamplePurpose",
    "SampleResults",
    "SampleStatus",
]

SamplePurpose = Literal["audit", "training"]
SampleStatus = Literal["open", "done"]


class Rate(View):
    successes: int
    trials: int
    value: float | None
    low: float | None
    high: float | None


class AgreementSummary(View):
    notes: int
    em: Rate
    em_higher: Rate
    em_lower: Rate
    em_other: int
    icd_precision: Rate
    icd_recall: Rate
    icd_f1: float | None
    icd_exact: Rate
    modifiers: Rate


class AgreementSides(View):
    bodha: AgreementSummary
    claim: AgreementSummary


class EmComparison(View):
    reference: str | None
    compared: str | None
    match: bool
    direction: Literal["match", "higher", "lower", "family", "absent"]


class IcdComparison(View):
    matched: int
    compared: int
    reference: int
    missing: list[str]
    extra: list[str]
    match: bool


class ModifierComparison(View):
    reference: list[str]
    compared: list[str]
    match: bool


class ElementComparison(View):
    em: EmComparison
    icd: IcdComparison
    modifiers: ModifierComparison


class ComparisonSides(View):
    bodha: ElementComparison
    claim: ElementComparison


class ClaimElements(View):
    em: str | None
    icd: list[str]
    modifiers: list[str]


class SampleOverview(View):
    id: str
    purpose: SamplePurpose
    scope: Literal["practice", "provider", "specialty"]
    provider_name: str | None
    specialty: str | None
    start: str | None
    end: str | None
    requested: int
    notes: int
    done: int
    status: SampleStatus
    reviewers: list[str]
    started_by: str | None
    started_at: str
    completed_at: str | None
    em: Rate
    em_claim: Rate


class SampleList(View):
    items: list[SampleOverview]


class SampleItemRow(View):
    id: str
    position: int
    provider_name: str
    service_date: str
    reviewer_name: str
    status: SampleStatus
    answer: ClaimElements | None
    bodha: ClaimElements | None
    claim: ClaimElements | None
    agreement: ComparisonSides | None


class ProviderAgreement(AgreementSides):
    provider_id: str
    provider_name: str


class SampleResults(View):
    sample: SampleOverview
    summary: AgreementSides
    providers: list[ProviderAgreement]
    items: list[SampleItemRow]


class OptionProvider(View):
    id: str
    name: str
    specialty: str | None


class OptionReviewer(View):
    id: str
    name: str
    role: Role


class QualityOptions(View):
    providers: list[OptionProvider]
    reviewers: list[OptionReviewer]
    specialties: list[str]
    default_size: int
    specialty_size: int


class AutonomyEligibility(View):
    eligible: bool
    reason: Literal["eligible", "no_audit", "too_few_notes", "agreement_low", "too_many_higher"]
    sample_id: str | None
    notes: int
    em_low: float | None
    higher_share: float | None


class ProviderAutonomy(View):
    id: str
    name: str
    credential: str
    specialty: str | None
    auto_approve: bool
    eligibility: AutonomyEligibility


class ProviderAutonomyList(View):
    items: list[ProviderAutonomy]


class LevelMixWindow(View):
    start: str
    end: str
    notes: int


class LevelMixCount(View):
    level: str
    recent: int
    prior: int


class LevelMixTest(View):
    statistic: float
    degrees_of_freedom: int
    p_value: float


class LevelMix(View):
    recent: LevelMixWindow
    prior: LevelMixWindow
    levels: list[LevelMixCount]
    test: LevelMixTest | None
    status: Literal["steady", "shifted", "not_enough"]
