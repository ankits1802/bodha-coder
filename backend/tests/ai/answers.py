from __future__ import annotations

import json
from datetime import date
from typing import Any

from app.ai.contracts import BilledCode, ReviewInputs, Section
from app.codes.mips_scope import MipsScope

NOTE = (
    "Follow-up visit. 67-year-old woman with type 2 diabetes and hypertension. A1c 8.4 on 11/02. BP 148/92. "
    "Assessment and plan: Type 2 diabetes with hyperglycemia, increase metformin to 1000 mg twice daily. "
    "Hypertension above goal, start amlodipine 5 mg daily. CKD, stable. Return in 3 months."
)
PDF = b"%PDF-1.4 scanned note without a text layer"
BILLED = (BilledCode("99215", "CPT"), BilledCode("E11.9", "ICD-10"))
ALL_SECTIONS: tuple[Section, ...] = ("em", "diagnoses", "code_review", "cdi", "audit", "mips")


def review_inputs(
    *,
    sections: tuple[Section, ...] = ALL_SECTIONS,
    note_text: str | None = NOTE,
    pdf: bytes | None = None,
    billed: tuple[BilledCode, ...] = BILLED,
    scope: MipsScope | None = None,
) -> ReviewInputs:
    return ReviewInputs(
        sections=frozenset(sections),
        setting="office",
        place_of_service="11",
        visit_type="Established patient",
        service_date=date(2026, 11, 20),
        billed_codes=billed,
        note_text=note_text,
        pdf=pdf,
        mips_scope=scope,
    )


def patient_answer() -> dict[str, Any]:
    return {"name": "Marisol Reyes", "age": 67, "sex": "female"}


def em_answer() -> dict[str, Any]:
    return {
        "code": "99214",
        "basis": "MDM",
        "mdm_level": "Moderate",
        "mdm_elements": {
            "problems": {"level": "Moderate", "reason": "Two chronic illnesses, diabetes not at goal."},
            "data": {"level": "Low", "reason": "A1c result reviewed."},
            "risk": {"level": "Moderate", "reason": "Prescription drug management."},
        },
        "time_minutes": None,
        "justification": "Two chronic illnesses, A1c reviewed, prescription drug management. Meets 2 of 3 at Moderate.",
        "evidence": ["increase metformin to 1000 mg twice daily"],
        "next_level_needs": ["A chronic illness with severe exacerbation, or extensive data"],
        "alternative_code": "99213",
        "alternative_reason": "Data is limited.",
        "modifiers": [],
        "add_on_codes": [],
    }


def diagnoses_answer() -> list[dict[str, Any]]:
    return [
        {
            "name": "Type 2 diabetes with hyperglycemia",
            "icd10": "E11.65",
            "status": "supported",
            "meat": "A1c evaluated and metformin increased.",
            "evidence": ["A1c 8.4 on 11/02"],
            "suggestion": "",
        },
        {
            "name": "CKD",
            "icd10": "N18.9",
            "status": "needs_specificity",
            "meat": "Assessed as stable.",
            "evidence": ["CKD, stable."],
            "suggestion": "Document the CKD stage.",
        },
    ]


def code_review_answer() -> dict[str, Any]:
    return {
        "em_reason": "Billed 99215 but the documentation supports moderate MDM.",
        "items": [
            {
                "code": "e11.9",
                "verdict": "replace",
                "suggested_code": "E11.65",
                "reason": "The note documents hyperglycemia.",
                "evidence": ["Type 2 diabetes with hyperglycemia"],
            },
            {
                "code": "99215",
                "verdict": "lower",
                "suggested_code": "99214",
                "reason": "Moderate MDM, no documented time.",
                "evidence": [],
            },
        ],
    }


def cdi_answer() -> dict[str, Any]:
    return {
        "specificityGaps": [
            {
                "finding": "Missing CKD stage",
                "currentDocumentation": "CKD, stable.",
                "recommendation": "Chronic kidney disease stage 3b",
                "rationale": "The stage selects the code.",
                "priority": "high",
                "targetSection": "",
                "replacesIcdCode": "N18.9",
                "suggestedIcdCode": "N18.32",
                "suggestedDiagnosis": "Chronic kidney disease, stage 3b",
                "suggestedText": "",
            }
        ],
        "codeLinkingOpportunities": [],
        "queryRecommendations": [
            {
                "query": "CKD is documented. Please clarify the stage of chronic kidney disease.",
                "reason": "The stage is needed for a specific code.",
                "options": ["Stage 3a", "Stage 3b", "Other"],
                "evidence": ["CKD, stable."],
                "targetSection": "assessment",
            }
        ],
        "overallCDIScore": 72,
        "summaryGuidance": "Specify the CKD stage.",
    }


def audit_answer() -> dict[str, Any]:
    return {
        "requiredElements": [{"element": "Chief complaint", "present": True, "location": "Opening line"}],
        "codingCompliance": [{"check": "E/M level support", "status": "fail", "finding": "99215 is not supported."}],
        "cmsCDICompliance": [{"standard": "Authentication", "compliant": False, "note": "No signature."}],
        "riskAreas": [{"risk": "Upcoding of the E/M level", "severity": "critical", "recommendation": "Code 99214."}],
        "overallComplianceScore": 78,
        "auditSummary": "Fair compliance.",
        "findings": [{"severity": "High", "title": "Missing provider signature", "detail": "Unsigned note."}],
    }


def mips_answer(*measures: dict[str, Any]) -> dict[str, Any]:
    return {"eligibleMeasures": list(measures) or [eye_exam_measure()], "fallbackMessage": None}


def eye_exam_measure(name: str = "Diabetes: Eye Exam") -> dict[str, Any]:
    return {
        "measureName": name,
        "mipsId": "MIPS #117",
        "eligibilityRationale": "A 67-year-old with type 2 diabetes.",
        "macro": "Diabetic eye exam by an eye care professional: [PLACEHOLDER: record the date and result].",
        "exceptionExclusion": None,
    }


def full_answer(**overrides: Any) -> dict[str, Any]:
    answer: dict[str, Any] = {
        "patient": patient_answer(),
        "em": em_answer(),
        "diagnoses": diagnoses_answer(),
        "code_review": code_review_answer(),
        "cdi": cdi_answer(),
        "audit": audit_answer(),
        "mips": mips_answer(),
    }
    answer.update(overrides)
    return {key: value for key, value in answer.items() if value is not None}


def as_text(answer: dict[str, Any]) -> str:
    return json.dumps(answer)
