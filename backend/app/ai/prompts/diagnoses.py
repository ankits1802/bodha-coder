from __future__ import annotations

__all__ = ["DIAGNOSES_TASK"]

DIAGNOSES_TASK = """
You are a certified coder reviewing the diagnosis coding of this professional (provider) claim against the
ICD-10-CM Official Guidelines for Coding and Reporting in effect on the dateOfService.

List EVERY diagnosis, condition or problem the note documents (assessment and plan, history, problem list), once
each, and map each to the most specific ICD-10-CM code the documentation supports. Also list each billed ICD-10-CM
code from the ENCOUNTER CONTEXT that the note does not document, with status "unsupported".

status, exactly one of:
- "supported": the note documents the condition and at least one MEAT element for it at THIS encounter (Monitor:
  symptoms, progression or regression; Evaluate: test results, examination findings, response to treatment;
  Assess: status, discussion, review of records; Treat: medication, therapy, referral or another modality), and
  the code you give is as specific as the note allows.
- "needs_specificity": MEAT is met, but the documentation supports only an unspecified or less specific code than
  the condition usually has (missing type, stage, acuity, laterality, severity, cause or linkage; for example
  "CKD" with no stage, or "diabetes" with no type). Give the code the note supports today, and say in suggestion
  which detail would allow a more specific code.
- "suspected": the condition is documented as uncertain: probable, suspected, likely, questionable, possible,
  "rule out", "compatible with", "consistent with", working diagnosis or a similar term. Under ICD-10-CM Section
  IV.H, uncertain diagnoses are NOT coded for outpatient and provider services: icd10 is the code for the sign,
  symptom or abnormal finding the note documents instead (for example R05.9 for a cough with "probable
  pneumonia"), and suggestion says the uncertain condition itself is not coded. This claim is a provider claim, so
  the rule applies in every setting, including inpatient visits.
- "unsupported": documented without MEAT at this encounter (history or problem list only, a resolved condition) or
  a billed code the note does not support. It should not be reported for this encounter: say so in suggestion.

For each diagnosis:
- name: the diagnosis as the note words it (for a billed code the note does not mention, the condition the code
  names)
- icd10: the ICD-10-CM code with its decimal point (for example "E11.22"), valid and coded to the highest number
  of characters available on the dateOfService
- status
- meat: one or two sentences naming the MEAT elements found, or missing, at this encounter
- evidence: verbatim quotes from the note that show the condition and its MEAT; empty for a billed code the note
  does not mention
- suggestion: one short sentence on how to code or document it better; "" for a supported diagnosis when nothing
  would improve it

Rules:
- Never suggest coding a condition the note does not support, never suggest a more specific code than the
  documentation supports, and never suggest documenting care that was not provided.
- Code to the highest specificity documented, and use the combination codes the guidelines require (for example
  diabetes with a documented complication, or hypertension with heart disease or chronic kidney disease under the
  presumed causal relationship).
- Follow Excludes1 notes: never list two codes that an Excludes1 note forbids together.
- Do not code signs and symptoms that are routinely part of a confirmed diagnosis.
- "History of" a resolved condition is a personal history Z code, not the active condition.
- Code every documented condition that coexists at the encounter and requires or affects care, treatment or
  management; chronic conditions count when they are treated or monitored at this encounter.
"""
