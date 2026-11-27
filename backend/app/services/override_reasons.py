from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from app.core.errors import Invalid
from app.models import OVERRIDE_NOTE_LENGTH, OVERRIDE_REASONS
from app.services.finding import Finding
from app.services.routing import CHANGE_KINDS

__all__ = [
    "OTHER_REASON",
    "PROPOSAL_ACTIONS",
    "REASON_LABELS",
    "REJECTING_CHOICES",
    "OverrideReason",
    "Reasoned",
    "checked_reason",
    "departing_choices",
    "departs_from_bodha",
    "missing_reasons",
    "reason_text",
]

OTHER_REASON = "other"
PROPOSAL_ACTIONS = ("lower", "raise", "replace", "add", "remove")
FLAGGING_ACTIONS = ("ask", "review")
REJECTING_CHOICES = ("keep", "skip")
REASON_LABELS = {
    "documentation": "Documentation supports the billed code",
    "payer_policy": "Payer policy",
    "provider_answer": "Provider's answer",
    "coding_guideline": "Coding guideline",
    "clinical_context": "Clinical context",
    "other": "Other",
}


@dataclass(frozen=True)
class OverrideReason:
    reason: str
    note: str | None


@dataclass(frozen=True)
class Reasoned:
    key: str
    choice: str
    reason: str | None


def checked_reason(reason: str, note: str | None) -> OverrideReason:
    if reason not in OVERRIDE_REASONS:
        raise Invalid(f"{reason} is not an override reason")
    text = (note or "").strip()
    if len(text) > OVERRIDE_NOTE_LENGTH:
        raise Invalid(f"an override note is at most {OVERRIDE_NOTE_LENGTH} characters")
    if reason == OTHER_REASON and not text:
        raise Invalid("write a short note when the reason is Other")
    return OverrideReason(reason, text or None)


def departs_from_bodha(finding: Finding, choice: str) -> bool:
    if finding.kind not in CHANGE_KINDS or choice not in REJECTING_CHOICES:
        return False
    if finding.action in PROPOSAL_ACTIONS:
        return True
    return finding.action in FLAGGING_ACTIONS and finding.code_before is not None and choice == "keep"


def departing_choices(finding: Finding, allowed: Iterable[str]) -> list[str]:
    return [choice for choice in allowed if departs_from_bodha(finding, choice)]


def missing_reasons(findings: Iterable[Finding], latest: Mapping[str, Reasoned]) -> list[str]:
    missing = []
    for finding in findings:
        decided = latest.get(finding.key)
        if decided is not None and decided.reason is None and departs_from_bodha(finding, decided.choice):
            missing.append(finding.key)
    return missing


def reason_text(reason: str | None, note: str | None) -> str | None:
    if reason is None:
        return None
    label = REASON_LABELS.get(reason, reason)
    return f"{label}: {note}" if note else label
