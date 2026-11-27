from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.codes.adjustment_reasons import describe_adjustment
from app.codes.em import describe_em
from app.services.remittance_835 import Adjustment
from app.services.remittance_outcomes import DOWNCODED

__all__ = ["AppealFacts", "appeal_letter", "money_text"]

MEDICARE = "medicare"
BLANK = "________________"


@dataclass(frozen=True)
class AppealFacts:
    practice_name: str
    payer_name: str | None
    plan_type: str
    outcome: str
    patient_name: str | None
    member_id: str | None
    payer_claim_number: str | None
    claim_ref: str | None
    service_date: date | None
    provider: str | None
    billed_code: str | None
    paid_code: str | None
    billed_cents: int | None
    paid_cents: int | None
    adjustments: tuple[Adjustment, ...]
    written_on: date


def appeal_letter(facts: AppealFacts) -> str:
    request = "redetermination" if facts.plan_type == MEDICARE else "reconsideration"
    lines = [
        facts.practice_name,
        _day(facts.written_on),
        "",
        f"To: {facts.payer_name or 'Claims appeals'}",
        f"Re: Request for {request}",
        "",
        *_claim_lines(facts),
        "",
        _argument(facts, request),
        "",
        "Enclosures:",
        "- Visit note for the date of service",
        "- Coding defense packet for the visit",
        "",
        "Sincerely,",
        "",
        BLANK,
        facts.practice_name,
    ]
    return "\n".join(lines) + "\n"


def _claim_lines(facts: AppealFacts) -> list[str]:
    adjustments = "; ".join(describe_adjustment(item.group, item.reason) for item in facts.adjustments)
    return [
        f"Patient: {facts.patient_name or BLANK}",
        f"Member ID: {facts.member_id or BLANK}",
        f"Payer claim number: {facts.payer_claim_number or BLANK}",
        f"Patient account number: {facts.claim_ref or BLANK}",
        f"Date of service: {_day(facts.service_date) if facts.service_date else BLANK}",
        f"Rendering provider: {facts.provider or BLANK}",
        f"Billed: {facts.billed_code or BLANK} {money_text(facts.billed_cents)}",
        f"Paid: {facts.paid_code or BLANK} {money_text(facts.paid_cents)}",
        f"Adjustments: {adjustments or 'none listed'}",
    ]


def _argument(facts: AppealFacts, request: str) -> str:
    billed = facts.billed_code or "the billed service"
    meaning = describe_em(billed) if facts.billed_code else None
    supported = f"{billed} ({meaning})" if meaning else billed
    if facts.outcome == DOWNCODED:
        changed = f"was paid as {facts.paid_code}" if facts.paid_code and facts.paid_code != billed else "was reduced"
        return (
            f"We request {request} of the payment for this service. The service billed as {billed} {changed}. "
            f"The documentation of the visit supports {supported}; the enclosed coding defense packet sets out "
            "the medical decision making or total time recorded in the note."
        )
    return (
        f"We request {request} of the denial of this service. The documentation of the visit supports "
        f"{supported} as billed and its medical necessity; the enclosed coding defense packet sets out the "
        "history, examination, medical decision making and diagnoses recorded in the note."
    )


def money_text(cents: int | None) -> str:
    if cents is None:
        return ""
    sign = "-" if cents < 0 else ""
    return f"{sign}${abs(cents) / 100:,.2f}"


def _day(day: date) -> str:
    return day.strftime("%d %B %Y")
