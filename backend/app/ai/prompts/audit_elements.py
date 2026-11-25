from __future__ import annotations

__all__ = ["REQUIRED_ELEMENTS"]

REQUIRED_ELEMENTS = """
# 1. REQUIRED ELEMENTS

Identify which kind of note this is, from the note itself and the ENCOUNTER CONTEXT's visitType and setting, and
verify the elements of the matching list below. When no list matches, use the Progress Note list. Since the 2021
(office) and 2023 (other settings) E/M guidelines, history and examination are "medically appropriate" and do not
set the E/M level: never mark a note deficient only because its review of systems or examination is short.

## SOAP Note
- Header (patient, provider, date of service)
- Chief complaint
- History of present illness
- Review of systems (as medically appropriate)
- Vital signs
- Physical examination (as medically appropriate)
- Assessment with each diagnosis
- MEAT evident for each assessed diagnosis (implicit or explicit)
- Plan with specific actions
- Medications reviewed or prescribed
- Follow-up plan

## H&P Note
- Header (patient, provider, date of service)
- Chief complaint
- Detailed history of present illness
- Past medical history
- Past surgical history
- Medications (home medications with dose, route and frequency)
- Allergies
- Family history
- Social history (tobacco, alcohol, drugs)
- Review of systems
- Vital signs
- Physical examination
- Data reviewed (labs, imaging)
- Assessment with diagnoses and MEAT
- Admission orders or plan

## Progress Note
- Header (patient, provider, date of service)
- Chief complaint or reason for the visit
- Interval history
- Physical examination (as medically appropriate)
- Review of systems (as medically appropriate)
- Data reviewed (labs, imaging)
- Assessment (updated problem list with status)
- Plan (interventions, follow-up)

## DAP Note (behavioral health)
- Header (patient, provider, date of service)
- Data (subjective and objective narrative)
- Mood and affect
- Thought process and content
- Suicidal and homicidal ideation assessed
- Assessment (clinical impression, diagnoses)
- Plan (interventions, medications, homework, follow-up)
- Time spent (when billed on time)

## Telehealth Initial Note
- Header (including the telehealth notation)
- Chief complaint
- Detailed history of present illness
- Past medical history
- Past surgical history
- Medications (home medications with dose, route and frequency)
- Allergies
- Family history
- Social history (tobacco, alcohol, drugs)
- Review of systems (as medically appropriate)
- Telehealth documentation (patient consent, audio-video or audio-only, patient location)
- Assessment with diagnoses and MEAT
- Plan (medications, referrals, follow-up)

## Telehealth Follow-up Note
- Header (including the telehealth notation)
- Chief complaint
- Interval history since the last visit
- Review of systems (as medically appropriate)
- Telehealth documentation (patient consent, audio-video or audio-only, patient location)
- Assessment (updated problem list with status)
- Plan (interventions, medication changes, follow-up)

## Annual Wellness Visit
An AWV is audited against the CMS elements that make G0438 or G0439 payable, NOT against a SOAP note's history,
review of systems or examination: a wellness visit has no chief complaint and requires no physical examination.
- Header (patient, provider, date of service)
- Health risk assessment completed
- Medical and family history reviewed
- Current providers and suppliers list
- Height, weight, BMI and blood pressure recorded
- Detection of cognitive impairment (a validated instrument, for example Mini-Cog or MoCA)
- Depression screening (a validated instrument, for example PHQ-9)
- Functional ability and safety review (activities of daily living, fall risk, home safety)
- Alcohol, tobacco and substance use screening
- Opioid use disorder screening
- Social determinants of health risk assessment
- Written screening schedule or personalized prevention plan
- Personalized health advice and referrals
- Advance care planning addressed
- Correct G-code (G0438 first AWV, G0439 subsequent)

## Advance Care Planning
An ACP note is audited against what makes CPT 99497 and 99498 payable, NOT against a SOAP note's history, review of
systems or examination: it documents a timed counselling discussion, not an examination.
- Header (patient, provider, date of service)
- Medical-necessity trigger documented (why this discussion, now)
- Face-to-face participants identified (patient, surrogate, family)
- Billing practitioner (physician or qualified health professional) named
- Chronic or serious diagnoses stated, with the change in status that makes the discussion necessary
- Existing advance directives reviewed, or recorded as none on file
- Substantive discussion documented: the elements explained AND a narrative of the values, questions and decisions,
  not a list of ticked boxes
- Total face-to-face time by the billing practitioner recorded in minutes
- Service statement present (the service was advance care planning, distinct from any other service billed today)
- Practitioner signature with date
- Telehealth statement present when the encounter was audio-video telehealth

## Nursing Facility Discharge Summary
A nursing facility discharge summary is audited against what makes CPT 99315 and 99316 payable, NOT against a SOAP
note's history, review of systems or examination: it documents the discharge-day management service and the stay
it ends.
- Header (patient, provider, date of service)
- Reason for the admission, with the qualifying stay where stated
- Course of the stay: response to therapy, complications, significant events, current status
- Admission date and discharge date
- Condition at discharge
- Discharge medications reconciled with the patient or caregiver
- Discharge disposition
- Discharge care instructions given to the patient or caregiver
- Follow-up arrangements or pending results
- Total discharge-day management time by the billing practitioner recorded in minutes
- Practitioner signature with date
- Telehealth statement present when the encounter was audio-video telehealth

## Wound Care Note
- Header (patient, provider, date of service)
- Assessment (clinical impression, diagnoses)
- Diagnostic data
- Healing factors
- Plan
- Significant findings
- Wound inventory
- Wound assessment (location, size, depth, tissue, drainage)

## Discharge Note
A discharge note is graded on the CMS discharge-summary elements, NOT on a SOAP note's history, review of systems or
examination: it summarises a completed stay rather than documenting a new encounter.
- Header (patient, provider, date of service)
- Reason for admission or presenting problem
- Hospital or stay course
- Discharge diagnoses
- Significant findings (labs, imaging, procedures)
- Discharge medications (with dose, route, frequency and changes)
- Condition and functional status at discharge
- Discharge instructions and patient education
- Follow-up arrangements (who, when, why)
- Disposition

For each element:
{
  "element": "[Element name]",
  "present": true | false,
  "location": "[Section where found]" (if present),
  "deficiency": "[What is missing]" (if not present)
}
"""
