from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import Field

from app.api.bodies import Body

MAX_SAMPLE = 500
MAX_TRAINING = 100
DEFAULT_TRAINING = 10


class SampleBody(Body):
    scope: Literal["practice", "provider", "specialty"]
    start: date
    end: date
    reviewer_ids: list[str] = Field(min_length=1, max_length=20)
    size: int | None = Field(default=None, ge=1, le=MAX_SAMPLE)
    provider_id: str | None = Field(default=None, max_length=36)
    specialty: str | None = Field(default=None, max_length=80)


class TrainingBody(Body):
    trainee_id: str = Field(min_length=1, max_length=36)
    start: date
    end: date
    size: int = Field(default=DEFAULT_TRAINING, ge=1, le=MAX_TRAINING)
    provider_id: str | None = Field(default=None, max_length=36)


class BlindAnswerBody(Body):
    em: str | None = Field(default=None, max_length=12)
    icd: list[str] = Field(default_factory=list, max_length=25)
    modifiers: list[str] = Field(default_factory=list, max_length=8)


class AutoApproveBody(Body):
    on: bool


class EvalCaseBody(Body):
    note_id: str = Field(min_length=1, max_length=36)
