from typing import Literal

from app.api.responses.base import PracticeRole, View
from app.models import USAGE_STEPS, USAGE_TASKS

__all__ = ["HqUsageFigures", "UsageFigures", "UsageSpread", "UsageStallFigures", "UsageTaskFigures"]

UsageTask = Literal[USAGE_TASKS]
UsageStep = Literal[USAGE_STEPS]


class UsageSpread(View):
    p25: float
    median: float
    p75: float


class UsageTaskFigures(View):
    task: UsageTask
    role: PracticeRole
    tasks: int
    completed: int
    people: int
    duration: UsageSpread | None
    first_decision: UsageSpread | None
    decided: int
    inputs_per_decision: UsageSpread | None
    keyboard_share: float | None


class UsageStallFigures(View):
    task: UsageTask
    step: UsageStep
    role: PracticeRole
    stalls: int
    people: int
    duration: UsageSpread | None


class UsageFigures(View):
    days: int
    tasks: list[UsageTaskFigures]
    stalls: list[UsageStallFigures]


class HqUsageFigures(UsageFigures):
    practices: int
