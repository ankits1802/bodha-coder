from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from app.codes.billing_codes import MAX_MODIFIERS, Code
from app.codes.em import is_em_code
from app.services.finding import CODE_CHANGE_ACTIONS, SEVERE_AUDIT, Finding

__all__ = [
    "ACCEPTING_CHOICES",
    "CHANGE_KINDS",
    "COMPLIANCE_LEVEL_GAP",
    "QUESTION_KINDS",
    "Placement",
    "choices_for",
    "claim",
    "has_diagnosis_codes",
    "open_questions",
    "place",
]

COMPLIANCE_LEVEL_GAP = 2
QUESTION_KINDS = ("cdi_query", "diagnosis")
CHANGE_KINDS = ("em", "diagnosis", "code_review", "modifier")
REPLACING_KINDS = ("em", "diagnosis", "code_review")
ACCEPTING_CHOICES = ("accept", "add")
ADDED_HEADLINES = (
    ("em", "Visit code missing"),
    ("diagnosis", "Diagnosis missing"),
    ("modifier", "Modifier missing"),
    ("code_review", "Add-on code missing"),
)


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


def has_diagnosis_codes(codes: Iterable[Code]) -> bool:
    return any(code.type == "ICD-10" for code in codes)


def place(
    findings: list[Finding], *, flagged: bool, cleared: bool, awaiting_provider: bool, billed_diagnoses: bool
) -> Placement:
    em = next((item for item in findings if item.kind == "em"), None)
    severe = [item for item in findings if item.kind == "audit_risk" and item.severity in SEVERE_AUDIT]
    gap = em.detail.get("level_difference", 0) if em else 0
    automatic = bool(severe) or (em is not None and em.action == "lower" and gap >= COMPLIANCE_LEVEL_GAP)
    if flagged or (automatic and not cleared):
        return _compliance_placement(flagged, gap)
    if awaiting_provider:
        return Placement("provider", "waiting_on_provider", "Waiting on provider")
    changes = [item for item in findings if _needs_coder(item, billed_diagnoses=billed_diagnoses)]
    if changes:
        return Placement("coder", "code_changes", _change_headline(em, changes))
    questions = open_questions(findings, choices_for(findings, {}))
    if questions:
        count = len(questions)
        return Placement("provider", "questions", f"{count} question{'s' if count > 1 else ''} to send")
    if any(_is_diagnosis_add(item) for item in findings):
        return Placement("approve", "matches", "Diagnoses added from the note")
    return Placement("approve", "matches", "Matches the note")


def _needs_coder(item: Finding, *, billed_diagnoses: bool) -> bool:
    if item.action not in CODE_CHANGE_ACTIONS or item.kind not in CHANGE_KINDS:
        return False
    return billed_diagnoses or not _is_diagnosis_add(item)


def _is_diagnosis_add(item: Finding) -> bool:
    return item.kind == "diagnosis" and item.action == "add"


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
    added = {item.kind for item in changes if item.action == "add"}
    headline = next((text for kind, text in ADDED_HEADLINES if kind in added), None)
    return headline or f"{len(changes)} code change{'s' if len(changes) > 1 else ''}"


def claim(billed: tuple[Code, ...], findings: list[Finding], choices: Mapping[str, str]) -> tuple[Code, ...]:
    accepted = [item for item in findings if choices[item.key] in ACCEPTING_CHOICES]
    by_before = {item.code_before: item for item in findings if item.code_before and item.kind in REPLACING_KINDS}
    kept: list[Code] = []
    for code in billed:
        item = by_before.get(code.code)
        kept += _apply(code, item, choices[item.key] if item else "keep")
    em = next((item for item in accepted if item.kind == "em" and item.code_before is None and item.code_after), None)
    if em is not None and choices[em.key] == "accept" and not any(code.type == "CPT" for code in kept):
        kept.insert(0, Code(em.code_after or "", "CPT"))
    codes = _unique(kept + [code for item in accepted if (code := _added_code(item)) is not None])
    for item in accepted:
        if item.kind == "modifier" and item.action == "add":
            codes = _with_modifier(codes, item)
    return tuple(codes)


def _apply(code: Code, item: Finding | None, choice: str) -> list[Code]:
    if item is None or choice not in ACCEPTING_CHOICES:
        return [code]
    if item.action == "remove":
        return []
    if item.code_after and item.action in ("lower", "raise", "replace"):
        return [Code(item.code_after, code.type, code.modifiers)]
    return [code]


def _added_code(item: Finding) -> Code | None:
    if item.action != "add" or item.code_before is not None or not item.code_after:
        return None
    if item.kind == "diagnosis":
        return Code(item.code_after, "ICD-10")
    if item.kind == "code_review":
        return Code(item.code_after, "CPT")
    return None


def _with_modifier(codes: list[Code], item: Finding) -> list[Code]:
    modifier = str(item.detail.get("modifier") or "")
    on_visit = bool(item.detail.get("on_visit"))
    for index, code in enumerate(codes):
        matches = is_em_code(code.code) if on_visit else code.code == item.code_before
        if code.type != "CPT" or not matches:
            continue
        if modifier and modifier not in code.modifiers and len(code.modifiers) < MAX_MODIFIERS:
            codes = [*codes[:index], Code(code.code, code.type, (*code.modifiers, modifier)), *codes[index + 1 :]]
        return codes
    return codes


def _unique(codes: list[Code]) -> list[Code]:
    seen: set[tuple[str, str]] = set()
    ordered: list[Code] = []
    for code in sorted(codes, key=lambda item: item.type != "CPT"):
        if (code.type, code.code) not in seen:
            seen.add((code.type, code.code))
            ordered.append(code)
    return ordered
