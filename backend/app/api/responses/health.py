from typing import Literal

from app.api.responses.base import View

__all__ = ["FAILED", "PASSED", "Health", "Readiness", "ReadinessChecks"]

PASSED = "ok"
FAILED = "unavailable"


class Health(View):
    status: Literal["ok"]


class ReadinessChecks(View):
    database: Literal[PASSED, FAILED]
    storage: Literal[PASSED, FAILED]


class Readiness(View):
    status: Literal["ready", "not ready"]
    checks: ReadinessChecks
