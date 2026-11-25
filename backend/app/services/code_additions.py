from __future__ import annotations

from collections.abc import Iterable

from app.ai.contracts import AddOnSuggestion, EmReview, ModifierSuggestion
from app.codes.billing_codes import MODIFIER_PATTERN, Code, is_known_cpt
from app.codes.modifiers import modifier_meaning
from app.services.finding import Finding

__all__ = ["ADD_ON_PREFIX", "MODIFIER_PREFIX", "add_on_findings", "modifier_findings", "visit_code"]

ADD_ON_PREFIX = "addon:"
MODIFIER_PREFIX = "modifier:"
LEVEL_CHANGES = ("lower", "raise", "replace", "add")


def visit_code(visit: Finding | None) -> str | None:
    if visit is None:
        return None
    if visit.action in LEVEL_CHANGES and visit.code_after:
        return visit.code_after
    return visit.code_before


def add_on_findings(em: EmReview, billed: tuple[Code, ...], visit: Finding | None) -> list[Finding]:
    taken = {code.code for code in billed if code.type == "CPT"} | {visit_code(visit)}
    found: dict[str, Finding] = {}
    for item in em.add_on_codes:
        code = item.code.strip().upper()
        if code and code not in taken and f"{ADD_ON_PREFIX}{code}" not in found:
            found[f"{ADD_ON_PREFIX}{code}"] = _add_on_finding(code, item)
    return list(found.values())


def modifier_findings(
    em: EmReview, billed: tuple[Code, ...], visit: Finding | None, add_ons: Iterable[Finding]
) -> list[Finding]:
    on_visit = visit_code(visit)
    billed_em = visit.code_before if visit is not None else None
    placed = {code.code: set(code.modifiers) for code in billed if code.type == "CPT"}
    targets = set(placed) | {on_visit} | {item.code_after for item in add_ons if item.action == "add"}
    found: dict[str, Finding] = {}
    for item in em.modifiers:
        modifier = item.modifier.strip().upper().lstrip("-")
        if not modifier:
            continue
        target = _target(item.code, on_visit, billed_em)
        is_visit = target == on_visit
        billed_as = billed_em if is_visit else target
        if modifier in placed.get(billed_as or "", set()):
            continue
        finding = _modifier_finding(modifier, target, item, is_visit=is_visit, targets=targets)
        found.setdefault(finding.key, finding)
    return list(found.values())


def _target(named: str, on_visit: str | None, billed_em: str | None) -> str | None:
    code = named.strip().upper()
    if not code or code in (on_visit, billed_em):
        return on_visit
    return code


def _add_on_finding(code: str, item: AddOnSuggestion) -> Finding:
    key = f"{ADD_ON_PREFIX}{code}"
    if not is_known_cpt(code):
        reason = " ".join(part for part in (f"{code} is not a 2026 physician fee schedule code.", item.reason) if part)
        return Finding(
            "code_review",
            key,
            "review",
            "Add-on code not confirmed",
            reason,
            evidence=tuple(item.evidence),
            detail={"code": code, "name": item.name},
            default_choice="keep",
        )
    title = item.name.strip() or "Add-on code"
    evidence = tuple(item.evidence)
    return Finding("code_review", key, "add", title, item.reason, None, code, evidence, detail={"add_on": True})


def _modifier_finding(
    modifier: str, target: str | None, item: ModifierSuggestion, *, is_visit: bool, targets: set[str | None]
) -> Finding:
    key = f"{MODIFIER_PREFIX}{modifier}" if is_visit else f"{MODIFIER_PREFIX}{target}:{modifier}"
    meaning = modifier_meaning(target, modifier) if target and MODIFIER_PATTERN.match(modifier) else None
    if target is None or target not in targets or meaning is None:
        return _unconfirmed_modifier(key, modifier, target, item)
    return Finding(
        "modifier",
        key,
        "add",
        meaning,
        item.reason,
        target,
        f"{target}-{modifier}",
        tuple(item.evidence),
        detail={"modifier": modifier, "code": target, "on_visit": is_visit},
    )


def _unconfirmed_modifier(key: str, modifier: str, target: str | None, item: ModifierSuggestion) -> Finding:
    where = f"{target}" if target else "the visit code"
    reason = " ".join(part for part in (f"Bodha does not add modifier {modifier} to {where}.", item.reason) if part)
    return Finding(
        "modifier",
        key,
        "review",
        "Modifier not confirmed",
        reason,
        evidence=tuple(item.evidence),
        detail={"modifier": modifier, "code": target},
        default_choice="keep",
    )
