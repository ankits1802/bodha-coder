from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date
from typing import Any, Literal, get_args

__all__ = ["DEMO_OUTCOMES", "BilledLine", "DemoCodeBook", "DemoOutcome", "DemoRequest", "demo_bundle"]

DemoOutcome = Literal["matches", "billed_too_high", "billed_too_low", "cdi_query", "audit_risk"]
DEMO_OUTCOMES: tuple[DemoOutcome, ...] = get_args(DemoOutcome)
Verdict = Literal["keep", "lower", "raise"]

MDM_LEVELS = ("Straightforward", "Low", "Moderate", "High")
DEFAULT_VISIT = "99213"
SCAN_TRANSCRIPT = "Scanned visit note."
MAX_QUOTE = 200
NEXT_LEVEL_NEEDS = ("Data reviewed or ordered for each problem", "Risk of the management chosen")
QUERY_OPTIONS = ("Controlled", "Uncontrolled", "Other")
CRITICAL_RISK = {
    "risk": "The visit level rests on management risk the plan does not document",
    "severity": "Critical",
    "recommendation": "Document the management options considered and the risk discussed with the patient.",
    "targetSection": "plan",
}
_STEPS: dict[DemoOutcome, int] = {"billed_too_high": -1, "billed_too_low": 1}
_PATIENT = re.compile(
    r"Patient:\s*(?P<name>\S.*?)\s{2,}DOB:\s*(?P<month>\d{2})/(?P<day>\d{2})/(?P<year>\d{4})\s+Sex:\s*(?P<sex>\w+)"
)
_AGE = re.compile(r"\b(\d{1,3})-year-old\b")
_PLAN_LINE = re.compile(r"^\s*\d+\.\s+\S.*$", re.M)
_WORD = re.compile(r"[a-z]{4,}")


@dataclass(frozen=True)
class BilledLine:
    code: str
    type: str


@dataclass(frozen=True)
class DemoRequest:
    outcome: DemoOutcome
    note: str
    billed: tuple[BilledLine, ...]
    service_date: date


@dataclass(frozen=True)
class DemoCodeBook:
    em_ladder: Callable[[str], Sequence[tuple[str, str]]]
    icd_name: Callable[[str, date], str | None]


@dataclass(frozen=True)
class _Visit:
    billed: str | None
    code: str
    mdm: str | None
    verdict: Verdict


def demo_bundle(parts: Sequence[str], request: DemoRequest, codes: DemoCodeBook) -> dict[str, Any]:
    visit = _visit(request, codes)
    names = {line.code: codes.icd_name(line.code, request.service_date) or line.code for line in _diagnoses_of(request)}
    answers: dict[str, Callable[[], Any]] = {
        "patient": lambda: _patient(request.note),
        "extracted_text": lambda: request.note or SCAN_TRANSCRIPT,
        "em": lambda: _em(visit, request.note),
        "diagnoses": lambda: _diagnoses(request, names),
        "code_review": lambda: _code_review(visit, request),
        "cdi": lambda: _cdi(request, names),
        "audit": lambda: _audit(request),
        "mips": lambda: {"eligibleMeasures": [], "fallbackMessage": None},
        "hcc": lambda: {"suspected": []},
    }
    return {part: answers[part]() for part in parts if part in answers}


def _diagnoses_of(request: DemoRequest) -> list[BilledLine]:
    return [line for line in request.billed if line.type == "ICD-10"]


def _visit(request: DemoRequest, codes: DemoCodeBook) -> _Visit:
    billed = next((line.code for line in request.billed if line.type == "CPT" and codes.em_ladder(line.code)), None)
    ladder = list(codes.em_ladder(billed or DEFAULT_VISIT))
    index = [code for code, _ in ladder].index(billed or DEFAULT_VISIT)
    step = _STEPS.get(request.outcome, 0) if billed else 0
    if not 0 <= index + step < len(ladder):
        step = -step
    if not 0 <= index + step < len(ladder):
        step = 0
    code, mdm = ladder[index + step]
    verdict: Verdict = "keep" if step == 0 else ("lower" if step < 0 else "raise")
    return _Visit(billed, code, mdm if mdm in MDM_LEVELS else None, verdict)


def _patient(note: str) -> dict[str, Any]:
    found, age = _PATIENT.search(note), _AGE.search(note)
    if found is None:
        return {"name": None, "age": int(age[1]) if age else None, "sex": None, "birth_date": None}
    return {
        "name": found["name"].strip(),
        "age": int(age[1]) if age else None,
        "sex": found["sex"],
        "birth_date": f"{found['year']}-{found['month']}-{found['day']}",
    }


def _em(visit: _Visit, note: str) -> dict[str, Any]:
    level = visit.mdm
    return {
        "code": visit.code,
        "basis": "MDM",
        "mdm_level": level,
        "mdm_elements": _elements(level) if level else None,
        "justification": f"Medical decision making is {level.lower()}." if level else "The note supports this visit.",
        "evidence": _plan_quotes(note)[:1],
        "next_level_needs": [] if level == "High" else list(NEXT_LEVEL_NEEDS),
        "modifiers": [],
        "add_on_codes": [],
    }


def _elements(level: str) -> dict[str, Any]:
    return {
        "problems": {"level": level, "reason": "Problems addressed in the assessment."},
        "data": {"level": level, "reason": "Results and records reviewed at the visit."},
        "risk": {"level": level, "reason": "Management chosen in the plan."},
    }


def _diagnoses(request: DemoRequest, names: dict[str, str]) -> list[dict[str, Any]]:
    return [
        {
            "name": names[line.code],
            "icd10": line.code,
            "status": "supported",
            "meat": "Assessed and managed in the plan.",
            "evidence": _matching_quote(request.note, names[line.code]),
            "suggestion": "",
        }
        for line in _diagnoses_of(request)
    ]


def _code_review(visit: _Visit, request: DemoRequest) -> dict[str, Any]:
    reason = "" if visit.verdict == "keep" else f"The documented decision making supports {visit.code}."
    return {"em_reason": reason, "items": [_verdict(line, visit, request.note) for line in request.billed]}


def _verdict(line: BilledLine, visit: _Visit, note: str) -> dict[str, Any]:
    if line.code != visit.billed or visit.verdict == "keep":
        return {"code": line.code, "verdict": "keep", "suggested_code": None, "reason": "Supported by the note."}
    return {
        "code": line.code,
        "verdict": visit.verdict,
        "suggested_code": visit.code,
        "reason": f"The documented decision making supports {visit.code}.",
        "evidence": _plan_quotes(note)[:1],
    }


def _cdi(request: DemoRequest, names: dict[str, str]) -> dict[str, Any]:
    queries = [_query(request, names)] if request.outcome == "cdi_query" else []
    return {
        "specificityGaps": [],
        "codeLinkingOpportunities": [],
        "queryRecommendations": queries,
        "overallCDIScore": 70 if queries else 92,
        "summaryGuidance": "Clarify one diagnosis with the provider." if queries else "Documentation is specific.",
    }


def _query(request: DemoRequest, names: dict[str, str]) -> dict[str, Any]:
    subject = next(iter(names.values()), "The documented condition")
    return {
        "query": f"{subject} is documented in the assessment. Please clarify whether the condition is controlled.",
        "reason": "Control status sets how specifically the diagnosis can be coded.",
        "options": list(QUERY_OPTIONS),
        "evidence": _matching_quote(request.note, subject),
        "targetSection": "assessment",
    }


def _audit(request: DemoRequest) -> dict[str, Any]:
    risky = request.outcome == "audit_risk"
    signed = "signed" in request.note.casefold()
    return {
        "requiredElements": [{"element": "Provider signature", "present": signed}],
        "codingCompliance": [{"check": "Visit level supported", "status": "Fail" if risky else "Pass"}],
        "cmsCDICompliance": [{"standard": "Signed and dated", "compliant": signed}],
        "riskAreas": [CRITICAL_RISK] if risky else [],
        "overallComplianceScore": 58 if risky else 94,
        "auditSummary": "High audit risk in the plan." if risky else "No audit risk found.",
        "findings": [],
    }


def _plan_quotes(note: str) -> list[str]:
    lines = [match.group(0).strip()[:MAX_QUOTE] for match in _PLAN_LINE.finditer(note)]
    if lines:
        return lines
    first = next((line.strip() for line in note.splitlines() if line.strip()), "")
    return [first[:MAX_QUOTE]] if first else []


def _matching_quote(note: str, name: str) -> list[str]:
    quotes = _plan_quotes(note)
    wanted = set(_WORD.findall(name.casefold()))
    ranked = sorted(quotes, key=lambda quote: -len(wanted & set(_WORD.findall(quote.casefold()))))
    return ranked[:1]
