from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field

from app.api.bodies import Body
from app.models import USAGE_OUTCOMES, USAGE_STEPS, USAGE_TASKS
from app.services.usage import MAX_DURATION_MS, MAX_EVENTS_PER_BATCH, MAX_INPUT_COUNT

__all__ = ["UsageBatchBody", "UsageStallBody", "UsageTaskBody"]

UsageTask = Literal[USAGE_TASKS]
UsageStep = Literal[USAGE_STEPS]
UsageOutcome = Literal[USAGE_OUTCOMES]
Duration = Annotated[int, Field(ge=0, le=MAX_DURATION_MS)]
InputCount = Annotated[int, Field(ge=0, le=MAX_INPUT_COUNT)]


class UsageTaskBody(Body):
    kind: Literal["task"]
    event_id: UUID
    task: UsageTask
    outcome: UsageOutcome
    duration_ms: Duration
    first_decision_ms: Duration | None = None
    key_inputs: InputCount = 0
    pointer_inputs: InputCount = 0
    key_decisions: InputCount = 0
    pointer_decisions: InputCount = 0


class UsageStallBody(Body):
    kind: Literal["stall"]
    event_id: UUID
    task: UsageTask
    step: UsageStep
    duration_ms: Duration


UsageEventBody = Annotated[UsageTaskBody | UsageStallBody, Field(discriminator="kind")]


class UsageBatchBody(Body):
    events: list[UsageEventBody] = Field(min_length=1, max_length=MAX_EVENTS_PER_BATCH)
