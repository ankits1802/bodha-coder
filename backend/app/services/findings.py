from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from app.ai.contracts import DiagnosisFinding, EmReview, ReviewReport
from app.codes.billing_codes import Code, is_known_cpt
from app.codes.em import compare_em, describe_em, is_em_code
from app.codes.hcc import hcc_model_for
from app.codes.icd import IcdRelease, format_icd
from app.services.code_additions import add_on_findings, modifier_findings
from app.services.finding import Finding
from app.services.risk_adjustment import risk_adjustment_findings

__all__ = [
    "Finding",
    "audit_findings",
    "build_findings",
    "cdi_findings",
    "cpt_findings",
    "diagnosis_findings",
    "em_finding",
    "mips_findings",
    "visit_findings",
]

MIPS_DETAIL_KEYS = (
    "macro",
    "status",
    "reportingCodes",
    "reportingCodesWithheld",
    "exceptionExclusion",
    "addedByOrganization",
)


def build_findings(report: ReviewReport, billed: tuple[Code, ...], icd: IcdRelease) -> list[Finding]:
    verdicts = {item.code.upper(): item for item in (report.code_review.items if report.code_review else [])}
    findings: list[Finding] = []
    if report.em is not None:
        findings += visit_findings(report.em, billed, report.code_review.em_reason if report.code_review else "")
    findings += cpt_findings(billed, verdicts)
    if report.diagnoses is not None:
        findings += diagnosis_findings(report.diagnoses, billed, icd)
    hcc_model = hcc_model_for(report.hcc.paymentYear) if report.hcc is not None else None
    findings += risk_adjustment_findings(report, billed, icd, hcc_model)
    findings += cdi_findings(_section(report.cdi))
    findings += audit_findings(_section(report.audit))
    findings += mips_findings(_section(report.mips))
    return findings


def visit_findings(em: EmReview, billed: tuple[Code, ...], em_reason: str) -> list[Finding]:
    visit = em_finding(em, billed, em_reason)
    add_ons = add_on_findings(em, billed, visit)
    return [visit, *modifier_findings(em, billed, visit, add_ons), *add_ons]


def em_finding(em: EmReview, billed: tuple[Code, ...], em_reason: str) -> Finding:
    billed_em = next((code.code for code in billed if code.type == "CPT" and is_em_code(code.code)), None)
    suggested = em.code if is_em_code(em.code) else None
    comparison = compare_em(billed_em, suggested)
    reasoning = " ".join(part for part in (em_reason, em.justification) if part)
    detail = {
        "family": comparison.family,
        "level_difference": comparison.level_difference,
        "basis": em.basis,
        "mdm_level": em.mdm_level,
        "mdm_elements": em.mdm_elements.model_dump() if em.mdm_elements else None,
        "time_minutes": em.time_minutes,
        "next_level_needs": em.next_level_needs,
        "alternative_code": em.alternative_code,
        "alternative_reason": em.alternative_reason,
        "model_code": em.code,
    }
    title = describe_em(suggested) if suggested else "Visit level could not be confirmed"
    action = comparison.direction if suggested else "review"
    default = "keep" if action in ("keep", "not_applicable") else "accept"
    return Finding(
        "em", "em", action, title or "", reasoning, billed_em, suggested, tuple(em.evidence), None, detail, default
    )


def cpt_findings(billed: tuple[Code, ...], verdicts: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    for code in billed:
        if code.type != "CPT" or is_em_code(code.code):
            continue
        verdict = verdicts.get(code.code)
        if not is_known_cpt(code.code):
            findings.append(
                Finding(
                    "code_review",
                    f"cpt:{code.code}",
                    "review",
                    "Not in the CMS fee schedule",
                    f"{code.code} is not a 2026 physician fee schedule code.",
                    code.code,
                )
            )
        elif verdict is not None and verdict.verdict != "keep":
            after = verdict.suggested_code if verdict.suggested_code and is_known_cpt(verdict.suggested_code) else None
            action = "remove" if verdict.verdict == "remove" else ("replace" if after else "review")
            findings.append(
                Finding(
                    "code_review",
                    f"cpt:{code.code}",
                    action,
                    "Procedure code",
                    verdict.reason,
                    code.code,
                    after,
                    tuple(verdict.evidence),
                )
            )
    return findings


def diagnosis_findings(diagnoses: list[DiagnosisFinding], billed: tuple[Code, ...], icd: IcdRelease) -> list[Finding]:
    documented = {format_icd(dx.icd10): dx for dx in diagnoses if dx.icd10}
    matched: set[str] = set()
    findings = [
        _billed_diagnosis(format_icd(code.code), documented, matched, icd) for code in billed if code.type == "ICD-10"
    ]
    for key, dx in documented.items():
        if key not in matched:
            findings += _unbilled_diagnosis(key, dx, icd)
    return findings


def _billed_diagnosis(
    code: str, documented: dict[str, DiagnosisFinding], matched: set[str], icd: IcdRelease
) -> Finding:
    entry = icd.get(code)
    exact = documented.get(code)
    sibling = None if exact else _same_category_documented(code, documented, icd)
    if exact is not None:
        matched.add(code)
        return _status_finding(code, exact, entry is not None and entry.billable)
    if sibling is not None:
        matched.add(format_icd(sibling.icd10))
        return Finding(
            "diagnosis",
            f"dx:{code}",
            "replace",
            sibling.name,
            _replacement_reason(code, format_icd(sibling.icd10), icd),
            code,
            format_icd(sibling.icd10),
            tuple(sibling.evidence),
            detail={"meat": sibling.meat},
        )
    if entry is None or not entry.billable:
        return Finding(
            "diagnosis",
            f"dx:{code}",
            "review",
            "Not a billable ICD-10-CM code",
            f"{code} is not billable in ICD-10-CM {icd.release}.",
            code,
            detail={"options": [item.code for item in icd.more_specific(code)[:8]]},
        )
    return Finding(
        "diagnosis",
        f"dx:{code}",
        "remove",
        entry.description,
        "Not found in the documentation. Remove it, or ask the provider to document it.",
        code,
    )


def _status_finding(code: str, dx: DiagnosisFinding, billable: bool) -> Finding:
    detail = {"meat": dx.meat, "suggestion": dx.suggestion}
    if not billable:
        return Finding(
            "diagnosis",
            f"dx:{code}",
            "review",
            dx.name,
            "Not a billable code for this date.",
            code,
            evidence=tuple(dx.evidence),
            detail=detail,
        )
    action, choice = {
        "supported": ("keep", "keep"),
        "needs_specificity": ("ask", "ask"),
        "suspected": ("ask", "ask"),
        "unsupported": ("remove", "accept"),
    }[dx.status]
    reasoning = dx.suggestion if action == "ask" and dx.suggestion else dx.meat
    return Finding(
        "diagnosis",
        f"dx:{code}",
        action,
        dx.name,
        reasoning,
        code,
        None,
        tuple(dx.evidence),
        detail=detail,
        default_choice=choice,
    )


def _unbilled_diagnosis(code: str, dx: DiagnosisFinding, icd: IcdRelease) -> list[Finding]:
    entry = icd.get(code)
    if dx.status == "unsupported" or entry is None or not entry.billable:
        return []
    action, choice = ("add", "add") if dx.status == "supported" else ("ask", "ask")
    return [
        Finding(
            "diagnosis",
            f"dx:{code}",
            action,
            dx.name,
            dx.meat or dx.suggestion,
            None,
            code,
            tuple(dx.evidence),
            detail={"meat": dx.meat, "suggestion": dx.suggestion},
            default_choice=choice,
        )
    ]


def _replacement_reason(code: str, documented_code: str, icd: IcdRelease) -> str:
    entry = icd.get(code)
    if entry is None or not entry.billable or icd.is_unspecified(code):
        return f"{code} is less specific than what the note documents."
    return f"The note documents {documented_code}, not {code}."


def _same_category_documented(
    code: str, documented: dict[str, DiagnosisFinding], icd: IcdRelease
) -> DiagnosisFinding | None:
    category = code[:3]
    candidates = [
        dx
        for key, dx in documented.items()
        if key[:3] == category
        and key != code
        and dx.status in ("supported", "needs_specificity")
        and (found := icd.get(key)) is not None
        and found.billable
    ]
    return candidates[0] if len(candidates) == 1 else None


def cdi_findings(cdi: dict[str, Any] | None) -> list[Finding]:
    if not cdi:
        return []
    gaps = [
        Finding(
            "cdi_gap",
            gap["id"],
            "info",
            gap["finding"],
            gap.get("rationale") or gap.get("recommendation", ""),
            gap.get("replacesIcdCode") or None,
            gap.get("suggestedIcdCode") or None,
            tuple(filter(None, [gap.get("currentDocumentation")])),
            gap.get("priority"),
            {"recommendation": gap.get("recommendation"), "suggested_text": gap.get("suggestedText")},
            "keep",
        )
        for gap in cdi.get("specificityGaps", [])
    ]
    queries = [
        Finding(
            "cdi_query",
            query["id"],
            "ask",
            query["query"],
            query.get("reason", ""),
            None,
            None,
            tuple(query.get("evidence") or []),
            None,
            {"options": query.get("options") or [], "suggested_text": query.get("suggestedText")},
            "ask",
        )
        for query in cdi.get("queryRecommendations", [])
    ]
    return gaps + queries


def audit_findings(audit: dict[str, Any] | None) -> list[Finding]:
    if not audit:
        return []
    risks = [
        Finding(
            "audit_risk",
            risk["id"],
            "info",
            risk["risk"],
            risk.get("recommendation", ""),
            severity=risk.get("severity"),
            default_choice="keep",
        )
        for risk in audit.get("riskAreas", [])
    ]
    notes = [
        Finding(
            "audit_finding",
            finding.get("id") or f"finding:{index}",
            "info",
            finding.get("title", ""),
            finding.get("detail", ""),
            severity=finding.get("severity"),
            default_choice="keep",
        )
        for index, finding in enumerate(audit.get("findings", []))
    ]
    return risks + notes


def mips_findings(mips: dict[str, Any] | None) -> list[Finding]:
    if not mips:
        return []
    return [
        Finding(
            "mips",
            f"mips:{measure.get('mipsId')}",
            "info",
            measure.get("measureName", ""),
            measure.get("eligibilityRationale", ""),
            default_choice="keep",
            detail={key: measure.get(key) for key in MIPS_DETAIL_KEYS},
        )
        for measure in mips.get("eligibleMeasures", [])
    ]


def _section(section: BaseModel | dict[str, Any] | None) -> dict[str, Any] | None:
    if isinstance(section, BaseModel):
        return section.model_dump()
    return section
