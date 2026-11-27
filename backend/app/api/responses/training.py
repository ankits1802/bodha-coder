from typing import Literal

from app.api.responses.base import View
from app.api.responses.notes import FindingAction, TextRevision
from app.api.responses.quality import AgreementSides, ClaimElements, ComparisonSides, SamplePurpose, SampleStatus
from app.models import SUGGESTION_KINDS

__all__ = [
    "AssignedSample",
    "BlindItem",
    "BlindProgress",
    "BlindStep",
    "BlindSubmitted",
    "TrainingFeedback",
    "TrainingOverview",
    "TrainingSuggestion",
]


class BlindProgress(View):
    id: str
    purpose: SamplePurpose
    total: int
    done: int


class BlindItem(View):
    id: str
    position: int
    texts: list[TextRevision]


class BlindStep(View):
    sample: BlindProgress
    item: BlindItem | None


class BlindSubmitted(View):
    id: str
    status: SampleStatus
    purpose: SamplePurpose


class AssignedSample(View):
    id: str
    purpose: SamplePurpose
    total: int
    done: int
    started_at: str


class TrainingOverview(View):
    sets: list[AssignedSample]
    scores: AgreementSides


class TrainingSuggestion(View):
    key: str
    kind: Literal[SUGGESTION_KINDS]
    action: FindingAction
    title: str
    reasoning: str
    code_before: str | None
    code_after: str | None
    evidence: list[str]


class TrainingFeedback(View):
    item_id: str
    sample_id: str
    answer: ClaimElements
    bodha: ClaimElements
    claim: ClaimElements
    agreement: ComparisonSides
    suggestions: list[TrainingSuggestion]
