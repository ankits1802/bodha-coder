from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from app.codes.billing_codes import Code
from app.services.findings import CODE_CHANGE_ACTIONS, SEVERE_AUDIT, Finding

COMPLIANCE_LEVEL_GAP = 2
QUESTION_KINDS = ("cdi_query", "diagnosis")


@dataclass(frozen=True)
class Placement:
    lane: str
    reason: str
    headline: str


def choices_for(findings: Iterable[Finding], decisions: Mapping[str, str]) -> dict[str, str]:
    return {finding.key: decisions.get(finding.key, finding.default_choice) for finding in findings}


def open_questions(findings: Iterable[Finding], choices: Mapping[str, str]) -> list[Finding]:
    return [
        item for item in findings if item.kind in QUESTION_KINDS and item.action == "ask" and choices[item.key] == "ask"
    ]


def place(findings: list[Finding], *, flagged: bool, cleared: bool, awaiting_provider: bool) -> Placement:
    em = next((item for item in findings if item.kind == "em"), None)
    severe = [item for item in findings if item.kind == "audit_risk" and item.severity in SEVERE_AUDIT]
    gap = em.detail.get("level_difference", 0) if em else 0
    automatic = bool(severe) or (em is not None and em.action == "lower" and gap >= COMPLIANCE_LEVEL_GAP)
    if flagged or (automatic and not cleared):
        return _compliance_placement(flagged, gap)
    if awaiting_provider:
        return Placement("provider", "waiting_on_provider", "Waiting on provider")
    changes = [
        item
        for item in findings
        if item.action in CODE_CHANGE_ACTIONS and item.kind in ("em", "diagnosis", "code_review")
    ]
    if changes:
        return Placement("coder", "code_changes", _change_headline(em, changes))
    questions = open_questions(findings, choices_for(findings, {}))
    if questions:
        count = len(questions)
        return Placement("provider", "questions", f"{count} question{'s' if count > 1 else ''} to send")
    return Placement("approve", "matches", "Matches the note")


def _compliance_placement(flagged: bool, gap: int) -> Placement:
    if flagged:
        return Placement("compliance", "flagged", "Flagged for compliance")
    if gap >= COMPLIANCE_LEVEL_GAP:
        return Placement("compliance", "levels_too_high", f"{gap} levels too high")
    return Placement("compliance", "audit_risk", "High audit risk")


def _change_headline(em: Finding | None, changes: list[Finding]) -> str:
    if em is not None and em.action == "lower":
        return "Billed too high"
    if em is not None and em.action == "raise":
        return "Billed too low"
    if em is not None and em.action == "replace":
        return "Wrong visit code family"
    if any(item.action == "add" for item in changes):
        return "Diagnosis missing"
    return f"{len(changes)} code change{'s' if len(changes) > 1 else ''}"


def claim(billed: tuple[Code, ...], findings: list[Finding], choices: Mapping[str, str]) -> tuple[Code, ...]:
    by_before = {item.code_before: item for item in findings if item.code_before and item.kind != "cdi_gap"}
    kept: list[Code] = []
    for code in billed:
        item = by_before.get(code.code)
        kept += _apply(code, item, choices[item.key] if item else "keep")
    added = [
        Code(item.code_after, "ICD-10")
        for item in findings
        if item.kind == "diagnosis"
        and item.code_before is None
        and item.code_after
        and choices[item.key] in ("add", "accept")
    ]
    if not any(code.type == "CPT" for code in kept):
        em = next(
            (item for item in findings if item.kind == "em" and item.code_before is None and item.code_after), None
        )
        if em is not None and choices[em.key] == "accept":
            kept.insert(0, Code(em.code_after or "", "CPT"))
    return tuple(_unique(kept + added))


def _apply(code: Code, item: Finding | None, choice: str) -> list[Code]:
    if item is None or choice not in ("accept", "add"):
        return [code]
    if item.action == "remove":
        return []
    if item.code_after and item.action in ("lower", "raise", "replace"):
        return [Code(item.code_after, code.type, code.modifiers)]
    return [code]


def _unique(codes: list[Code]) -> list[Code]:
    seen: set[tuple[str, str]] = set()
    ordered: list[Code] = []
    for code in sorted(codes, key=lambda item: item.type != "CPT"):
        if (code.type, code.code) not in seen:
            seen.add((code.type, code.code))
            ordered.append(code)
    return ordered
