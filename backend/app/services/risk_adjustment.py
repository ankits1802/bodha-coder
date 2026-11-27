from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from app.ai.contracts import PatientFacts, ReviewReport
from app.ai.hcc import SuspectedCondition
from app.codes.billing_codes import Code
from app.codes.hcc import HCC_MODEL_NAME, HccModel, HccPatient, Segment, payment_year_age, segment_for, sex_code
from app.codes.icd import IcdRelease, format_icd
from app.services.finding import Finding

__all__ = [
    "AGE_FROM_BIRTH_DATE",
    "AGE_FROM_NOTE",
    "DOCUMENTED_STATUSES",
    "RISK_SUMMARY_KEY",
    "SUSPECTED_PREFIX",
    "risk_adjustment_findings",
]

RISK_SUMMARY_KEY = "hcc"
SUSPECTED_PREFIX = "hcc:"
RISK_SUMMARY_TITLE = "Risk adjustment"
DOCUMENTED_STATUSES = ("supported", "needs_specificity")
AGE_FROM_BIRTH_DATE = "birth_date"
AGE_FROM_NOTE = "note"
SEGMENT_LABELS: Mapping[Segment, str] = MappingProxyType(
    {"aged": "Community, non-dual, aged", "disabled": "Community, non-dual, disabled"}
)


@dataclass(frozen=True)
class _HccAge:
    years: int | None
    source: str | None


@dataclass(frozen=True)
class _HccSets:
    billed: Mapping[str, tuple[str, ...]]
    documented: Mapping[str, tuple[str, ...]]
    billed_paid: frozenset[str]
    documented_paid: frozenset[str]


def risk_adjustment_findings(
    report: ReviewReport, billed: tuple[Code, ...], icd: IcdRelease, model: HccModel | None
) -> list[Finding]:
    review = report.hcc
    if review is None:
        return []
    if model is None:
        return [_summary_finding({"model": review.model, "payment_year": review.paymentYear, "available": False})]
    age = _hcc_age(report.patient, model.payment_year)
    patient = HccPatient(age.years, sex_code(report.patient.sex))
    diagnoses = report.diagnoses or []
    billed_codes = [format_icd(code.code) for code in billed if code.type == "ICD-10"]
    documented = [
        format_icd(dx.icd10) for dx in diagnoses if dx.status in DOCUMENTED_STATUSES and _billable(icd, dx.icd10)
    ]
    known = set(billed_codes) | {format_icd(dx.icd10) for dx in diagnoses if dx.icd10}
    suspected = [_suspected_finding(item, model, patient, icd, known) for item in review.suspected]
    summary = _summary(model, patient, billed_codes, documented, age=age)
    return [summary, *(item for item in suspected if item is not None)]


def _hcc_age(patient: PatientFacts, payment_year: str) -> _HccAge:
    years = payment_year_age(patient.birth_date, payment_year) if patient.birth_date else None
    if years is not None:
        return _HccAge(years, AGE_FROM_BIRTH_DATE)
    return _HccAge(patient.age, AGE_FROM_NOTE if patient.age is not None else None)


def _summary(
    model: HccModel, patient: HccPatient, billed: list[str], documented: list[str], *, age: _HccAge
) -> Finding:
    billed_by = _codes_by_hcc(model, billed, patient)
    documented_by = _codes_by_hcc(model, documented, patient)
    sets = _HccSets(billed_by, documented_by, model.payment_hccs(billed_by), model.payment_hccs(documented_by))
    segment = segment_for(patient.age)
    detail = {
        "model": HCC_MODEL_NAME,
        "payment_year": model.payment_year,
        "available": True,
        "age": age.years,
        "age_from": age.source,
        "segment": SEGMENT_LABELS[segment] if segment else None,
        "score_billed": model.score(billed_by, segment) if segment else None,
        "score_documented": model.score(documented_by, segment) if segment else None,
        "categories": _category_rows(model, sets, segment),
    }
    return _summary_finding(detail)


def _summary_finding(detail: dict[str, Any]) -> Finding:
    return Finding("diagnosis", RISK_SUMMARY_KEY, "info", RISK_SUMMARY_TITLE, "", detail=detail, default_choice="keep")


def _codes_by_hcc(model: HccModel, codes: Iterable[str], patient: HccPatient) -> dict[str, tuple[str, ...]]:
    found: dict[str, list[str]] = {}
    for code in codes:
        for hcc in model.hccs_for(code, patient):
            if code not in found.setdefault(hcc, []):
                found[hcc].append(code)
    return {hcc: tuple(sorted(items)) for hcc, items in found.items()}


def _category_rows(model: HccModel, sets: _HccSets, segment: Segment | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for hcc in sorted(sets.billed_paid | sets.documented_paid, key=_hcc_number):
        status = _status(model, hcc, sets)
        if status is None:
            continue
        codes = sorted(set(sets.billed.get(hcc, ())) | set(sets.documented.get(hcc, ())))
        factor = model.factor(hcc, segment) if segment else None
        rows.append({"hcc": hcc, "label": model.label(hcc), "status": status, "codes": codes, "factor": factor})
    return rows


def _status(model: HccModel, hcc: str, sets: _HccSets) -> str | None:
    billed, documented = hcc in sets.billed_paid, hcc in sets.documented_paid
    if billed and documented:
        return "captured"
    if documented:
        return None if model.is_trumped(hcc, sets.billed_paid) else "missed"
    return None if model.is_trumped(hcc, sets.documented_paid) else "unsupported"


def _suspected_finding(
    item: SuspectedCondition, model: HccModel, patient: HccPatient, icd: IcdRelease, known: set[str]
) -> Finding | None:
    code = format_icd(item.icd10)
    if code in known or not _billable(icd, code):
        return None
    hccs = model.payment_hccs(model.hccs_for(code, patient))
    if not hccs:
        return None
    return Finding(
        "diagnosis",
        f"{SUSPECTED_PREFIX}{code}",
        "ask",
        item.query,
        item.indicators,
        evidence=tuple(item.evidence),
        detail={
            "options": item.options,
            "condition": item.condition,
            "icd10": code,
            "hccs": [{"hcc": hcc, "label": model.label(hcc)} for hcc in sorted(hccs, key=_hcc_number)],
        },
        default_choice="ask",
    )


def _billable(icd: IcdRelease, code: str) -> bool:
    entry = icd.get(code) if code else None
    return entry is not None and entry.billable


def _hcc_number(hcc: str) -> int:
    return int(hcc.removeprefix("HCC"))
