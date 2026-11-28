from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.fhir_client import FhirClient
from app.adapters.guarded_http import OutboundError, OutboundHttp
from app.adapters.smart_backend import discover
from app.core.deps import Actor
from app.core.errors import Conflict
from app.models import EhrConnection, utcnow
from app.services.audit_log import record_access
from app.services.ehr_keys import NOT_SET_UP, current_key, ehr_ready, smart_client
from app.services.ehr_settings import latest_connection
from app.services.rate_limits import EHR_TESTS_PER_PRACTICE, hit

__all__ = ["CHECK_STEPS", "CONNECTION_TESTED", "check_connection"]

CONNECTION_TESTED = "connection to the EHR tested"
CHECK_STEPS = ("configuration", "token", "capability")
FHIR_R4 = "4."


@dataclass(frozen=True)
class StepResult:
    step: str
    passed: bool
    detail: str

    def as_json(self) -> dict[str, Any]:
        return {"step": self.step, "passed": self.passed, "detail": self.detail}


async def check_connection(db: AsyncSession, actor: Actor, http: OutboundHttp) -> dict[str, Any]:
    if not ehr_ready():
        raise Conflict(NOT_SET_UP)
    connection = await latest_connection(db, actor.practice_id)
    if connection is None:
        raise Conflict("save the EHR connection first")
    key = await current_key(db, actor.practice_id)
    if key is None:
        raise Conflict("create a key first")
    await hit(db, EHR_TESTS_PER_PRACTICE, actor.practice_id)
    client = smart_client(connection, key)
    async with http.connect() as guarded:
        fhir = FhirClient(guarded, connection.base_url, client)
        steps = await _run_steps(
            [
                ("configuration", lambda: _configuration(fhir, connection)),
                ("token", lambda: _token(fhir)),
                ("capability", lambda: _capability(fhir)),
            ]
        )
    passed = len(steps) == len(CHECK_STEPS) and all(step.passed for step in steps)
    failed = next((step.step for step in steps if not step.passed), None)
    record_access(db, actor, CONNECTION_TESTED, detail="passed" if passed else f"failed at {failed}")
    await db.commit()
    return {"passed": passed, "tested_at": utcnow().isoformat(), "steps": [step.as_json() for step in steps]}


async def _run_steps(steps: list[tuple[str, Callable[[], Awaitable[str]]]]) -> list[StepResult]:
    results: list[StepResult] = []
    for name, check in steps:
        try:
            results.append(StepResult(name, True, await check()))
        except OutboundError as error:
            results.append(StepResult(name, False, error.message))
            break
    return results


async def _configuration(fhir: FhirClient, connection: EhrConnection) -> str:
    found = await discover(fhir.http, fhir.base_url)
    if found.token_endpoint != connection.token_endpoint:
        raise OutboundError("the EHR now names another token endpoint; save the connection again")
    return f"token endpoint {found.token_endpoint}"


async def _token(fhir: FhirClient) -> str:
    token = await fhir.authorize()
    return f"granted {token.scope}" if token.scope else "token issued"


async def _capability(fhir: FhirClient) -> str:
    statement = await fhir.capability()
    version = statement.get("fhirVersion")
    if not isinstance(version, str) or not version.startswith(FHIR_R4):
        raise OutboundError(f"the EHR speaks FHIR {version or 'of an unknown version'}, and Bodha reads FHIR R4")
    return f"the EHR serves FHIR {version}"
