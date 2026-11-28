from __future__ import annotations

from typing import Annotated

from pydantic import Field, StringConstraints

from app.api.bodies import Body
from app.codes.practice_measures import CODES_PER_OUTCOME
from app.models import MEASURE_IDENTIFIER_LENGTH, MEASURE_NAME_LENGTH, MEASURE_SCOPE_LENGTH, MEASURE_TO_MEET_LENGTH

__all__ = [
    "MEASURE_NAME_MIN",
    "MEASURE_TEXT_MIN",
    "PracticeMeasureBody",
    "PracticeMeasureChangeBody",
    "PracticeMeasureRetireBody",
]

MEASURE_NAME_MIN = 3
MEASURE_TEXT_MIN = 10
REPORTING_CODE_LENGTH = 12

ReportingCodeText = Annotated[str, StringConstraints(min_length=1, max_length=REPORTING_CODE_LENGTH)]


class PracticeMeasureBody(Body):
    name: str = Field(min_length=MEASURE_NAME_MIN, max_length=MEASURE_NAME_LENGTH)
    identifier: str | None = Field(default=None, max_length=MEASURE_IDENTIFIER_LENGTH)
    in_scope: str = Field(min_length=MEASURE_TEXT_MIN, max_length=MEASURE_SCOPE_LENGTH)
    out_of_scope: str | None = Field(default=None, max_length=MEASURE_SCOPE_LENGTH)
    to_meet: str = Field(min_length=MEASURE_TEXT_MIN, max_length=MEASURE_TO_MEET_LENGTH)
    met_codes: list[ReportingCodeText] = Field(default_factory=list, max_length=CODES_PER_OUTCOME)
    not_met_codes: list[ReportingCodeText] = Field(default_factory=list, max_length=CODES_PER_OUTCOME)


class PracticeMeasureChangeBody(PracticeMeasureBody):
    expected_version: int = Field(ge=1)


class PracticeMeasureRetireBody(Body):
    expected_version: int = Field(ge=1)
