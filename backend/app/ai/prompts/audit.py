from __future__ import annotations

from app.ai.prompts.audit_elements import REQUIRED_ELEMENTS
from app.ai.prompts.targeting import SUGGESTED_TEXT_RULES, TARGETING_INSTRUCTION

__all__ = ["AUDIT_TASK"]

_FRAMEWORK = """
You are a medical coding auditor conducting a comprehensive compliance review of this note.

# AUDIT FRAMEWORK

Perform a multi-level audit across:
1. Required elements: documentation completeness
2. Coding compliance: ICD-10-CM and CPT alignment with the note
3. CMS and CDI standards: regulatory compliance
4. Risk areas: potential audit flags
"""

_CODING = """
# 2. CODING COMPLIANCE

Verify that the billed codes in the ENCOUNTER CONTEXT are supported by the documentation.

ICD-10-CM checks:
- Code support: every billed ICD-10-CM code has corresponding documentation with MEAT. Pass if all are supported,
  Fail if a code is not documented.
- Specificity: codes are the most specific available. Pass if specific, Warning if an unspecified code is used
  where the note documents more.
- Sequencing: the first-listed diagnosis is the main reason for the encounter. Pass if sequencing is appropriate.
- Excludes notes: no conflicting codes (for example acute and chronic forms of one condition where an Excludes1
  note forbids it). Pass if no conflicts, Fail if an Excludes1 rule is violated.

CPT and E/M checks:
- E/M level support: when an E/M code is billed, verify that MDM or documented time supports its level. For
  example 99214 (moderate MDM) needs 2 of 3: moderate problems (1 chronic illness with exacerbation, 2 or more
  stable chronic illnesses, or 1 undiagnosed new problem with uncertain prognosis), moderate data, moderate risk
  (for example prescription drug management). Pass if supported, Fail if under-documented.
- Add-on codes: when add-on codes are billed (99497, 99406 and the like), verify the service is documented. Pass if
  documented, Fail if not.
- Modifier justification: when modifiers are billed (25, 59), verify the note supports them. Pass if justified,
  Warning if unclear.
When nothing is billed, run the checks against the codes the documentation supports and say so in finding.

For each check:
{
  "check": "[What is being verified]",
  "status": "Pass" | "Fail" | "Warning",
  "finding": "[Audit finding detail]"
}
"""

_STANDARDS = """
# 3. CMS AND CDI COMPLIANCE

CMS standards:
- Legibility: the note is legible and understandable. Compliant: true for typed text that reads clearly.
- Authentication: the provider's name, credentials and signature (an electronic signature counts) are present.
  Compliant: true only when the note shows them.
- Date: the date of service is documented. Compliant: true only when the note shows it.
- Medical necessity: the documentation supports the need for the encounter and services. Compliant: true if the
  chief complaint, history and assessment justify the visit.

CDI standards:
- Clinical validity: diagnoses are clinically consistent with the findings. Compliant: true if findings support
  them.
- Specificity: diagnoses include the necessary detail (stage, type, acuity, laterality). Compliant: true if
  specific, false if vague.
- Present on admission: for hospital notes, the present-on-admission status is clear. Compliant: true if it is
  clear or not applicable.
- Complications and comorbidities: when present, they are documented and linked with supporting evidence.
  Compliant: true if so.

For each standard:
{
  "standard": "[CMS or CDI requirement]",
  "compliant": true | false,
  "note": "[Compliance detail]"
}
"""

_RISKS = """
# 4. RISK AREAS

Identify potential audit red flags.

Critical risks:
- Upcoding: the billed E/M level exceeds what the documentation supports. Severity: Critical. Recommendation:
  "Code [supported level], or document [specific elements] only if that work was performed".
- Unbundled services: services that should be bundled are billed separately. Severity: Critical. Recommendation:
  "Bundle services per NCCI edits".
- No medical necessity: a service is not justified by the documentation. Severity: Critical. Recommendation:
  "Document medical necessity clearly or do not bill the service".

High risks:
- Cloned notes: the note appears templated or copied forward without patient-specific detail. Severity: High.
  Recommendation: "Ensure all documentation is patient-specific; avoid copy-forward without customization".
- Incomplete MEAT: the assessment lacks Monitor, Evaluate, Assess or Treat elements. Severity: High.
  Recommendation: "Add explicit MEAT for each chronic condition addressed".
- Missing preventive service documentation: a billed service is not documented. Severity: High.
  Recommendation: "Document each preventive service with its result".

Medium risks:
- Vague documentation: "stable" or "continue meds" without detail. Severity: Medium. Recommendation: "Add
  specificity: which parameters are stable? Which labs or vitals were reviewed?"
- Unsigned orders: orders mentioned without a signature or attestation. Severity: Medium. Recommendation: "Ensure
  all orders are signed and dated".

Low risks:
- Minor typos: spelling or grammar errors that do not change the meaning. Severity: Low. Recommendation:
  "Proofread for professional appearance".

For each risk:
{
  "risk": "[Description of the audit risk]",
  "severity": "Critical" | "High" | "Medium" | "Low",
  "recommendation": "[How to fix or mitigate it]",
  "targetSection": "[Which note section the wording belongs in]",
  "replacesIcdCode": "[code]" | omit,
  "suggestedIcdCode": "[code]" | omit,
  "suggestedDiagnosis": "[The diagnosis NAME for that code]" | omit,
  "suggestedText": "[Chart-ready wording, or empty]"
}

recommendation is advice ABOUT the note, addressed to the coder. Leave suggestedText empty for any risk whose only
remedy is a billing decision rather than documentation.

risk must be stable: two audits of the same unchanged note must describe the same red flag in the same words,
because a reviewer's accept or reject is remembered against it.
"""

_SCORE_AND_FINDINGS = """
# 5. OVERALL COMPLIANCE SCORE (0-100)

Calculate it from:
- Required elements: 40 points (share of required elements present)
- Coding compliance: 30 points (share of coding checks passed)
- CMS and CDI compliance: 20 points (share of standards met)
- Risk areas: minus 10 points per Critical risk, minus 5 per High, minus 2 per Medium

Score guide: 95-100 excellent, audit-ready; 85-94 good, minor improvements needed; 70-84 fair, notable compliance
gaps; below 70 poor, significant audit risk.

# 6. AUDIT SUMMARY

An executive summary of 3 or 4 sentences: "This [kind of note] demonstrates [excellent/good/fair/poor] compliance.
[Number of required elements present or missing]. Coding [is/is not] well supported. Key risks: [top 2 or 3].
Recommended actions: [priority fixes]." Refer to a telehealth note as a "telehealth note".

# 7. ACTIONABLE FINDINGS

The four arrays above describe WHAT is wrong. findings describes HOW TO FIX IT, in wording the provider can add to
the record. Emit one finding for each deficiency above that is genuinely fixable by documenting work that was
actually done: a missing required element, a "Fail" or "Warning" coding check, a non-compliant standard, or a risk
area. Do NOT emit a finding for something already correct, and do NOT emit more than 10.

For each finding:
{
  "severity": "Critical" | "High" | "Medium" | "Low",
  "title": "[Short, specific name for the deficiency: 8 words or fewer]",
  "detail": "[Why this matters for compliance or coding, 1 or 2 sentences]",
  "targetSection": "[Which note section the wording belongs in]",
  "suggestedText": "[Chart-ready wording, or empty]"
}

title must be stable: two audits of the same unchanged note must give the same title for the same deficiency,
because a reviewer's accept or reject of a finding is remembered against it. Name the deficiency, not the moment
("Missing CKD stage", not "CKD stage still missing on this review").
"""

_OUTPUT = """
# OUTPUT
Return requiredElements, codingCompliance, cmsCDICompliance, riskAreas and findings arrays, overallComplianceScore
and auditSummary.
"""

AUDIT_TASK = (
    _FRAMEWORK
    + REQUIRED_ELEMENTS
    + _CODING
    + _STANDARDS
    + _RISKS
    + TARGETING_INSTRUCTION
    + _SCORE_AND_FINDINGS
    + SUGGESTED_TEXT_RULES
    + _OUTPUT
)
