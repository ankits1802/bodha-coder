from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date

from app.codes.billing_codes import Code
from app.codes.fees import ClaimEstimate
from app.services.estimates import claim_estimate, money
from app.services.finding import Finding
from app.services.review_actions import allowed_choices
from app.services.routing import ACCEPTING_CHOICES, claim

__all__ = ["ClaimContext", "amount_change", "amount_changes"]


@dataclass(frozen=True)
class ClaimContext:
    billed: tuple[Code, ...]
    findings: list[Finding]
    choices: Mapping[str, str]
    place_code: str
    service_date: date


def amount_changes(context: ClaimContext) -> dict[str, float | None]:
    return {finding.key: amount_change(context, finding) for finding in context.findings}


def amount_change(context: ClaimContext, finding: Finding) -> float | None:
    allowed = allowed_choices(finding)
    if len(allowed) < 2 or allowed[0] not in ACCEPTING_CHOICES:
        return None
    accepted = _priced(context, finding.key, allowed[0])
    rejected = _priced(context, finding.key, allowed[1])
    if accepted is None or rejected is None:
        return None
    if all(line.amount is None for line in (*accepted.lines, *rejected.lines)):
        return None
    return money(accepted.total - rejected.total)


def _priced(context: ClaimContext, key: str, choice: str) -> ClaimEstimate | None:
    choices = {**context.choices, key: choice}
    return claim_estimate(claim(context.billed, context.findings, choices), context.place_code, context.service_date)
