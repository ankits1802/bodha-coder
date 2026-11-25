from __future__ import annotations

import copy
import re
from datetime import UTC, datetime
from typing import Any

from app.codes.mips_catalog import (
    NO_NURSING_FACILITY_VISIT_NOTE as _NO_NURSING_FACILITY_VISIT,
)
from app.codes.mips_catalog import (
    SPECIFIED_ADDED_MEASURE_IDS,
    VERIFIED_MIPS_MEASURES,
    addable_measure,
    org_added_entry,
)
from app.codes.mips_scope import MipsScope

SPEC_BUNDLES: dict[str, dict[str, str]] = {
    "MIPS CQM": {
        "url": "https://qpp-cm-prod-content.s3.amazonaws.com/uploads/3565/2026-MIPS-CQM-Specifications-and-Supporting-Documents.zip",
        "sha256": "4198f636ebe80760d8de6ee10f7f286726197f4fa01d5fb298589b5de72ce796",
    },
    "Medicare Part B Claims": {
        "url": "https://qpp-cm-prod-content.s3.amazonaws.com/uploads/3564/2026-Part-B-Claims-Measure-Specifications-and-Supporting-Documents.zip",
        "sha256": "787f5c7a1333b3cae229c4b58dee373ebb21f843cbfb24e12370fc21cf232f10",
    },
}

SPEC_VERSION = "CMS 2026 MIPS quality measure specifications, Version 10.0, December 2025"

ROLES = ("met", "not-met", "exception", "exclusion")

_CQM_SPEC = "https://qpp.cms.gov/docs/QPP_quality_measure_specifications/CQM-Measures/2026_Measure_{}_MIPSCQM.pdf"
_CLAIMS_SPEC = (
    "https://qpp.cms.gov/docs/QPP_quality_measure_specifications/Claims-Registry-Measures/"
    "2026_Measure_{}_MedicarePartBClaims.pdf"
)


_LONG_TERM_CARE = (
    "CMS excludes patients 66 and older who reside in long-term care for more than 90 "
    "consecutive days in the measurement period (or are in an Institutional Special Needs Plan), "
)
_CONFIRM_THE_STAY = " Confirm the resident's stay before reporting."


def _row(code: str, role: str, meaning: str, *, criterion: int | None = None) -> dict[str, Any]:
    return {"code": code, "role": role, "meaning": meaning, "criterion": criterion}


def _measure(
    measure_id: str,
    *,
    claims: bool,
    rows: list[dict[str, Any]],
    note: str | None = None,
    mvp_only: bool = False,
) -> dict[str, Any]:
    cqm = _CQM_SPEC.format(measure_id)
    specifications = [cqm] + ([_CLAIMS_SPEC.format(measure_id)] if claims else [])
    collection = "MIPS CQM and Medicare Part B Claims" if claims else "MIPS CQM"
    if mvp_only:
        collection += " (MIPS Value Pathway reporting only)"
    return {
        "collectionType": collection,
        "specifications": specifications,
        "codes": [{**row, "source": cqm} for row in rows],
        "note": note,
    }


MIPS_REPORTING_CODES: dict[str, dict[str, Any]] = {
    "001": _measure(
        "001",
        claims=True,
        note=(
            "Inverse measure (a lower performance rate is better): 'met' here means the most "
            "recent HbA1c or GMI is above 9.0%, missing, or not performed — poor control. "
            + _LONG_TERM_CARE
            + "and patients 66 and older with frailty plus an advanced illness or a dispensed "
            "dementia medication."
            + _CONFIRM_THE_STAY
            + " "
            + _NO_NURSING_FACILITY_VISIT
        ),
        rows=[
            _row("M1371", "not-met", "Most recent glycemic status assessment (HbA1c or GMI) level < 7.0%"),
            _row("M1372", "not-met", "Most recent glycemic status assessment (HbA1c or GMI) level >= 7.0% and < 8.0%"),
            _row("M1373", "not-met", "Most recent glycemic status assessment (HbA1c or GMI) level >= 8.0% and <= 9.0%"),
            _row("M1211", "met", "Most recent glycemic status assessment (HbA1c or GMI) level > 9.0%"),
            _row("M1212", "met", "Glycemic status assessment (HbA1c or GMI) level is missing, or was not performed during the measurement period"),
            _row("G9687", "exclusion", "Hospice services provided to patient any time during the measurement period"),
            _row("G9988", "exclusion", "Palliative care services provided to patient any time during the measurement period"),
            _row("G2081", "exclusion", "Patients age 66 and older in Institutional Special Needs Plans (SNP) or residing in long-term care with a POS code 32, 33, 34, 54 or 56 for more than 90 consecutive days during the measurement period"),
            _row("G2090", "exclusion", "Patients 66 years of age and older with at least one claim/encounter for frailty during the measurement period AND a dispensed medication for dementia during the measurement period or the year prior to the measurement period"),
            _row("G2091", "exclusion", "Patients 66 years of age and older with at least one claim/encounter for frailty during the measurement period AND an advanced illness diagnosis during the measurement period or the year prior to the measurement period"),
        ],
    ),
    "048": _measure(
        "048",
        claims=False,
        note=_NO_NURSING_FACILITY_VISIT,
        rows=[
            _row("1090F", "met", "Presence or absence of urinary incontinence assessed"),
            _row("1090F-8P", "not-met", "Presence or absence of urinary incontinence not assessed, reason not otherwise specified"),
            _row("G9693", "exclusion", "Patient use of hospice services any time during the measurement period"),
        ],
    ),
    "117": _measure(
        "117",
        claims=False,
        note=(
            _LONG_TERM_CARE
            + "and patients 66 and older with frailty plus an advanced illness or a dispensed "
            "dementia medication."
            + _CONFIRM_THE_STAY
            + " "
            + _NO_NURSING_FACILITY_VISIT
        ),
        rows=[
            _row("M1220", "met", "Dilated retinal eye exam with interpretation by an ophthalmologist or optometrist or artificial intelligence (AI) interpretation documented and reviewed; with evidence of retinopathy"),
            _row("M1221", "met", "Dilated retinal eye exam with interpretation by an ophthalmologist or optometrist or artificial intelligence (AI) interpretation documented and reviewed; without evidence of retinopathy"),
            _row("2024F", "met", "7 standard field stereoscopic retinal photos with interpretation by an ophthalmologist or optometrist documented and reviewed; with evidence of retinopathy"),
            _row("2025F", "met", "7 standard field stereoscopic retinal photos with interpretation by an ophthalmologist or optometrist documented and reviewed; without evidence of retinopathy"),
            _row("2026F", "met", "Eye imaging validated to match diagnosis from 7 standard field stereoscopic retinal photos results documented and reviewed; with evidence of retinopathy"),
            _row("2033F", "met", "Eye imaging validated to match diagnosis from 7 standard field stereoscopic retinal photos results documented and reviewed; without evidence of retinopathy"),
            _row("3072F", "met", "Low risk for retinopathy (no evidence of retinopathy in the prior year)"),
            _row("M1429", "met", "Retinal exam finding with evidence of retinopathy in left, right or both eyes with severity level documented"),
            _row("M1430", "met", "Retinal exam finding without evidence of retinopathy in both eyes with severity level documented (in measurement year or in the prior year)"),
            _row("2022F-8P", "not-met", "Dilated eye exam was not performed, reason not otherwise specified"),
            _row("2024F-8P", "not-met", "Dilated eye exam was not performed, reason not otherwise specified"),
            _row("2026F-8P", "not-met", "Dilated eye exam was not performed, reason not otherwise specified"),
            _row("G9714", "exclusion", "Patient is using hospice services any time during the measurement period"),
            _row("G9994", "exclusion", "Patient is using palliative care services any time during the measurement period"),
            _row("G2105", "exclusion", "Patient age 66 or older in Institutional Special Needs Plans (SNP) or residing in long-term care with POS code 32, 33, 34, 54, or 56 for more than 90 consecutive days during the measurement period"),
            _row("G2106", "exclusion", "Patients 66 years of age and older with at least one claim/encounter for frailty during the measurement period AND a dispensed medication for dementia during the measurement period or the year prior to the measurement period"),
            _row("G2107", "exclusion", "Patients 66 years of age and older with at least one claim/encounter for frailty during the measurement period AND an advanced illness diagnosis during the measurement period or the year prior to the measurement period"),
            _row("M1428", "exclusion", "Patients who have bilateral absence of eyes any time during the patient's history through the end of the measurement period"),
        ],
    ),
    "128": _measure(
        "128",
        claims=True,
        mvp_only=True,
        note=(
            "2026: available only for MIPS Value Pathway (MVP) reporting, not traditional MIPS; "
            "not telehealth eligible (a telehealth encounter is not in the denominator)."
        ),
        rows=[
            _row("G8420", "met", "BMI is documented within normal parameters and no follow-up plan is required"),
            _row("G8417", "met", "BMI is documented above normal parameters and a follow-up plan is documented"),
            _row("G8418", "met", "BMI is documented below normal parameters and a follow-up plan is documented"),
            _row("G2181", "exception", "BMI not documented due to medical reason OR patient refusal of height or weight measurement"),
            _row("G9716", "exception", "BMI is documented as being outside of normal parameters, follow-up plan is not completed for documented medical reason"),
            _row("G8421", "not-met", "BMI not documented and no reason is given"),
            _row("G8419", "not-met", "BMI documented outside normal parameters, no follow-up plan documented, no reason given"),
            _row("G9996", "exclusion", "Documentation stating the patient has received or is currently receiving palliative or hospice care"),
            _row("G9997", "exclusion", "Documentation of patient pregnancy anytime during the measurement period prior to and including the current encounter"),
        ],
    ),
    "130": _measure(
        "130",
        claims=False,
        note=(
            "A visit measure: reported at every eligible visit, for a patient of any age. The 'met' "
            "code attests that the current medication list was documented using all immediate "
            "resources available on the date of the encounter, and it is also the code when the "
            "clinician documents that the patient takes no medications."
        ),
        rows=[
            _row("G8427", "met", "Eligible clinician attests to documenting in the medical record they obtained, updated, or reviewed the patient's current medications"),
            _row("G8430", "exception", "Documentation of a medical reason(s) for not documenting, updating, or reviewing the patient's current medications list (e.g., patient is in an acute health crisis where time is of the essence and delay of treatment would jeopardize the patient's health status)"),
            _row("G8428", "not-met", "Current list of medications not documented as obtained, updated, or reviewed by the eligible clinician, reason not given"),
        ],
    ),
    "134": _measure(
        "134",
        claims=True,
        rows=[
            _row("G8431", "met", "Screening for depression is documented as being positive AND a follow-up plan is documented"),
            _row("G8510", "met", "Screening for depression is documented as negative, a follow-up plan is not required"),
            _row("G8433", "exception", "Screening for depression not completed, documented patient or medical reason"),
            _row("G8432", "not-met", "Depression screening not documented, reason not given"),
            _row("G8511", "not-met", "Screening for depression documented as positive, follow-up plan not documented, reason not given"),
            _row("G9717", "exclusion", "Documentation stating the patient has had a diagnosis of bipolar disorder"),
        ],
    ),
    "226": _measure(
        "226",
        claims=True,
        note=(
            "Three submission criteria: 1 = tobacco use screening; 2 = cessation intervention for a "
            "patient identified as a tobacco user (each criterion-2 code is submitted together with "
            "the criterion-1 tobacco-user code); 3 = the overall rate. CMS scores performance on "
            "criterion 2 and takes data completeness from criterion 1. "
            + _NO_NURSING_FACILITY_VISIT
        ),
        rows=[
            _row("G9902", "met", "Patient screened for tobacco use AND identified as a tobacco user", criterion=1),
            _row("G9903", "met", "Patient screened for tobacco use AND identified as a tobacco non-user", criterion=1),
            _row("G9905", "not-met", "Patient not screened for tobacco use", criterion=1),
            _row("G9906", "met", "Patient identified as a tobacco user received tobacco cessation intervention during the measurement period or in the six months prior to the measurement period (counseling and/or pharmacotherapy)", criterion=2),
            _row("G9908", "not-met", "Patient identified as tobacco user did not receive tobacco cessation intervention during the measurement period or in the six months prior to the measurement period (counseling and/or pharmacotherapy)", criterion=2),
            _row("G0030", "met", "Patient screened for tobacco use AND received tobacco cessation intervention during the measurement period or in the six months prior to the measurement period (counseling, pharmacotherapy, or both), if identified as a tobacco user", criterion=3),
            _row("1036F", "met", "Current tobacco non-user", criterion=3),
            _row("G0029", "not-met", "Tobacco screening not performed OR tobacco cessation intervention not provided during the measurement period or in the six months prior to the measurement period", criterion=3),
            _row("M1159", "exclusion", "Hospice services provided to patient any time during the measurement period"),
        ],
    ),
    "236": _measure(
        "236",
        claims=True,
        note=(
            "Submit one systolic and one diastolic code; performance is met only when BOTH are the "
            "'met' codes (systolic < 140 mmHg and diastolic < 90 mmHg). "
            + _LONG_TERM_CARE
            + "patients 66 to 80 with frailty plus an advanced illness or a dispensed dementia "
            "medication, and patients 81 and older with frailty."
            + _CONFIRM_THE_STAY
            + " "
            + _NO_NURSING_FACILITY_VISIT
        ),
        rows=[
            _row("G8752", "met", "Most recent systolic blood pressure < 140 mmHg"),
            _row("G8753", "not-met", "Most recent systolic blood pressure >= 140 mmHg"),
            _row("G8754", "met", "Most recent diastolic blood pressure < 90 mmHg"),
            _row("G8755", "not-met", "Most recent diastolic blood pressure >= 90 mmHg"),
            _row("G8756", "not-met", "No documentation of blood pressure measurement, reason not given"),
            _row("G9740", "exclusion", "Hospice services given to patient any time during the measurement period"),
            _row("G0031", "exclusion", "Palliative care services given to patient any time during the measurement period"),
            _row("G9231", "exclusion", "Documentation of end stage renal disease (ESRD), dialysis, renal transplant before or during the measurement period or pregnancy during the measurement period"),
            _row("G9910", "exclusion", "Patients age 66 or older in Institutional Special Needs Plans (SNP) or residing in long-term care with POS code 32, 33, 34, 54, or 56 for more than 90 consecutive days during the measurement period"),
            _row("G2115", "exclusion", "Patients 66 - 80 years of age with at least one claim/encounter for frailty during the measurement period AND a dispensed medication for dementia during the measurement period or the year prior to the measurement period"),
            _row("G2116", "exclusion", "Patients 66 - 80 years of age with at least one claim/encounter for frailty during the measurement period AND an advanced illness diagnosis during the measurement period or the year prior to the measurement period"),
            _row("G2118", "exclusion", "Patients 81 years of age and older with at least one claim/encounter for frailty during the measurement period"),
        ],
    ),
    "326": _measure(
        "326",
        claims=False,
        rows=[
            _row("G8967", "met", "FDA-approved oral anticoagulant is prescribed"),
            _row("G8968", "exception", "Documentation of medical reason(s) for not prescribing an FDA-approved anticoagulant (e.g., present or planned atrial appendage occlusion or ligation or patient being currently enrolled in a clinical trial related to AF/atrial flutter treatment)"),
            _row("G8969", "exception", "Documentation of patient reason(s) for not prescribing an oral anticoagulant that is FDA approved for the prevention of thromboembolism (e.g., patient preference for not receiving anticoagulation)"),
            _row("G9928", "not-met", "FDA-approved anticoagulant not prescribed, reason not given"),
            _row("G9929", "exclusion", "Patient with transient or reversible cause of AF (e.g., pneumonia, hyperthyroidism, pregnancy, cardiac surgery)"),
            _row("G9930", "exclusion", "Patients who are receiving comfort care only"),
            _row("G9931", "exclusion", "Documentation of CHA2DS2-VASc risk score of 0 or 1 for men; or 0, 1, or 2 for women"),
            _row("G0044", "exclusion", "Patients with moderate or severe mitral stenosis"),
            _row("G0043", "exclusion", "Patients with mechanical prosthetic heart valve"),
        ],
    ),
    "431": _measure(
        "431",
        claims=False,
        note=(
            "Three submission criteria: 1 = unhealthy alcohol use screening; 2 = brief counseling for "
            "a patient identified as an unhealthy alcohol user; 3 = the overall rate. CMS scores "
            "performance on criterion 2 and takes data completeness from criterion 1. "
            + _NO_NURSING_FACILITY_VISIT
        ),
        rows=[
            _row("G2196", "met", "Patient identified as an unhealthy alcohol user when screened for unhealthy alcohol use using a systematic screening method", criterion=1),
            _row("G2197", "met", "Patient screened for unhealthy alcohol use using a systematic screening method and not identified as an unhealthy alcohol user", criterion=1),
            _row("G2199", "not-met", "Patient not screened for unhealthy alcohol use using a systematic screening method", criterion=1),
            _row("G2200", "met", "Patient identified as an unhealthy alcohol user received brief counseling", criterion=2),
            _row("G2202", "not-met", "Patient did not receive brief counseling if identified as an unhealthy alcohol user", criterion=2),
            _row("G9621", "met", "Patient identified as an unhealthy alcohol user when screened for unhealthy alcohol use using a systematic screening method and received brief counseling", criterion=3),
            _row("G9622", "met", "Patient not identified as an unhealthy alcohol user when screened for unhealthy alcohol use using a systematic screening method", criterion=3),
            _row("G9624", "not-met", "Patient not screened for unhealthy alcohol use using a systematic screening method or patient did not receive brief counseling if identified as an unhealthy alcohol user", criterion=3),
            _row("M1164", "exclusion", "Patients with dementia any time during the patient's history through the end of the measurement period"),
            _row("M1165", "exclusion", "Patients who use hospice services any time during the measurement period"),
        ],
    ),
    "493": _measure(
        "493",
        claims=False,
        note=(
            "Five submission criteria, one per vaccine, all required: 1 = influenza (19+), "
            "2 = Td or Tdap (19+), 3 = recombinant zoster (50+), 4 = pneumococcal (66+), "
            "5 = hepatitis B (19+). Performance is a weighted average of the five. A "
            "patient-reported vaccine, recorded in the medical record, counts."
        ),
        rows=[
            _row("M1168", "met", "Patient received an influenza vaccine on or between July 1 of the year prior to the measurement period and June 30 of the measurement period", criterion=1),
            _row("M1169", "exception", "Documentation of medical reason(s) for not administering influenza vaccine (e.g., prior anaphylaxis due to the influenza vaccine)", criterion=1),
            _row("M1170", "not-met", "Patient did not receive an influenza vaccine on or between July 1 of the year prior to the measurement period and June 30 of the measurement period", criterion=1),
            _row("M1171", "met", "Patient received at least one Td vaccine or one Tdap vaccine between nine years prior to the encounter and the end of the measurement period", criterion=2),
            _row("M1172", "exception", "Documentation of medical reason(s) for not administering Td or Tdap vaccine (e.g., prior anaphylaxis due to the Td or Tdap vaccine or history of encephalopathy within seven days after a previous dose of a Td-containing vaccine)", criterion=2),
            _row("M1173", "not-met", "Patient did not receive at least one Td vaccine or one Tdap vaccine between nine years prior to the encounter and the end of the measurement period", criterion=2),
            _row("M1174", "met", "Patient received at least two doses of the herpes zoster recombinant vaccine (at least 28 days apart) on October 20, 2017, through the end of the measurement period", criterion=3),
            _row("M1175", "exception", "Documentation of medical reason(s) for not administering zoster vaccine (e.g., prior anaphylaxis due to the zoster vaccine)", criterion=3),
            _row("M1238", "exception", "Documentation that administration of second recombinant zoster vaccine could not occur during the performance period due to the recommended 2-6 month interval between doses (i.e., first dose received after October 31)", criterion=3),
            _row("M1176", "not-met", "Patient did not receive two doses of the herpes zoster recombinant vaccine (at least 28 days apart) on October 20, 2017, through the end of the measurement period", criterion=3),
            _row("M1177", "met", "Patient received any pneumococcal conjugate or polysaccharide vaccine on or after their 19th birthday and before the end of the measurement period", criterion=4),
            _row("M1178", "exception", "Documentation of medical reason(s) for not administering pneumococcal vaccine (e.g., prior anaphylaxis due to the pneumococcal vaccine)", criterion=4),
            _row("M1179", "not-met", "Patient did not receive any pneumococcal conjugate or polysaccharide vaccine, on or after their 19th birthday and before or during measurement period", criterion=4),
            _row("M1468", "met", "Patient received recommended doses of hepatitis B vaccination based on age", criterion=5),
            _row("M1469", "exception", "Patient has a history of hepatitis B illness or received a hepatitis B surface antigen, hepatitis B surface antibody, or total antibody to hepatitis B core antigen test with a positive result any time before or during the measurement period", criterion=5),
            _row("M1470", "exception", "Documentation of medical reason(s) for not administering hepatitis B vaccine (e.g., prior anaphylaxis due to the hepatitis B vaccine)", criterion=5),
            _row("M1471", "exception", "Documentation that patient is a Medicare Fee-For-Service beneficiary and without additional supplementary insurance coverage for whom Hep B vaccination is not reimbursable under current Medicare Part B coverage rules", criterion=5),
            _row("M1472", "not-met", "Patient did not receive recommended doses of hepatitis B vaccination based on age", criterion=5),
            _row("M1167", "exclusion", "In hospice or using hospice services during the measurement period"),
        ],
    ),
}


SPECIFIED_REPORTING_CODES: dict[str, dict[str, Any]] = {
    "047": _measure(
        "047",
        claims=True,
        note=(
            "A patient measure: reported at least once per patient in the performance period. "
            "'Met' also covers a previously developed advance care plan that is still valid in the "
            "medical record: the clinician need not review it with the patient annually. CMS requires "
            "the code each year, to confirm that the plan in the record is still appropriate or that a "
            "new discussion was started. When the "
            "patient's cultural or spiritual beliefs preclude a discussion of advance care planning, "
            "CMS's instruction is to submit 1124F. Not for a visit in the emergency department."
        ),
        rows=[
            _row("1123F", "met", "Advance Care Planning discussed and documented; advance care plan or surrogate decision maker documented in the medical record"),
            _row("1124F", "met", "Advance Care Planning discussed and documented in the medical record; patient did not wish or was not able to name a surrogate decision maker or provide an advance care plan"),
            _row("1123F-8P", "not-met", "Advance Care Planning not documented, reason not otherwise specified"),
            _row("G9692", "exclusion", "Hospice services received by patient any time during the measurement period"),
        ],
    ),
    "126": _measure(
        "126",
        claims=False,
        note=(
            "A patient measure: reported at least once per patient in the performance period; an exam "
            "documented on the encounter date or in the 12 months before it counts. The exam is a 10-g "
            "monofilament test plus at least one of: vibration with a 128-Hz tuning fork, pinprick "
            "sensation, ankle reflexes or vibration perception threshold. Not telehealth eligible (a "
            "telehealth encounter is not in the denominator). CMS 2026: this measure may be submitted "
            "by non-medical doctor/doctor of osteopathic medicine (MD/DO) MIPS eligible clinicians."
        ),
        rows=[
            _row("G8404", "met", "Lower extremity neurological exam performed and documented"),
            _row("G2179", "exception", "Clinician documented that patient had medical reason for not performing lower extremity neurological exam"),
            _row("G8405", "not-met", "Lower extremity neurological exam not performed"),
            _row("G2178", "exclusion", "Clinician documented that patient was not an eligible candidate for lower extremity neurological exam measure, for example patient bilateral amputee; patient has condition that would not allow them to accurately respond to a neurological exam (dementia, Alzheimer's, etc.); patient has previously documented diabetic peripheral neuropathy with loss of protective sensation"),
        ],
    ),
    "155": _measure(
        "155",
        claims=False,
        note=(
            "A patient measure: reported at least once per patient in the performance period, only for a "
            "patient 65 or older with two or more falls, or any fall with injury, in the past year (the "
            "patient's report is enough). CMS also lists, with the denominator, a quality-data code for "
            "the fall-risk screen that documents that history; this card does not show it. The plan of "
            "care must include balance, strength and gait training: documented training or "
            "instructions, a referral to an exercise program with at least one of balance, strength or "
            "gait, or a referral to physical therapy. Its parts may be documented at different visits "
            "within 12 months."
        ),
        rows=[
            _row("0518F", "met", "Falls plan of care documented"),
            _row("0518F-1P", "exception", "Patient not ambulatory, bed ridden, immobile, confined to chair, wheelchair bound, dependent on helper pushing wheelchair, independent in wheelchair or minimal help in wheelchair"),
            _row("0518F-8P", "not-met", "Falls plan of care not documented, reason not otherwise specified"),
            _row("G9720", "exclusion", "Hospice services for patient occurred any time during the measurement period"),
        ],
    ),
    "238": _measure(
        "238",
        claims=False,
        note=(
            "Inverse measure (a lower performance rate is better): 'met' here means the patient was "
            "ORDERED at least two high-risk medications from the same drug class, on different dates "
            "of service. CMS: a high-risk medication previously prescribed by another provider is not "
            "counted unless the submitting provider also ordered a high-risk medication for the "
            "patient from the same drug class. Two submission criteria: 1 = CMS's Tables 1-3 (high risk at any dose; "
            "nitrofurantoin over 90 days' supply; digoxin over 0.125 mg a day; doxepin over 6 mg a "
            "day); 2 = antipsychotics and benzodiazepines (Table 4), except for appropriate "
            "diagnoses. CMS uses criterion 1's rate for performance."
        ),
        rows=[
            _row("G9367", "met", "At least two orders for high-risk medications from the same drug class", criterion=1),
            _row("G9368", "not-met", "At least two orders for high-risk medications from the same drug class not ordered", criterion=1),
            _row("M1209", "met", "At least two orders for high-risk medications from the same drug class, (Table 4), without appropriate diagnoses", criterion=2),
            _row("M1210", "not-met", "At least two orders for high-risk medications from the same drug class, (Table 4), not ordered", criterion=2),
            _row("G0032", "not-met", "Two or more antipsychotic prescriptions ordered for patients who had a diagnosis of schizophrenia, schizoaffective disorder, or bipolar disorder on or between January 1 of the year prior to the measurement period and the Index Prescription Start Date (IPSD) for antipsychotics", criterion=2),
            _row("G0033", "not-met", "Two or more benzodiazepine prescriptions ordered for patients who had a diagnosis of seizure disorders, rapid eye movement sleep behavior disorder, benzodiazepine withdrawal, ethanol withdrawal, or severe generalized anxiety disorder on or between January 1 of the year prior to the measurement period and the IPSD for benzodiazepines", criterion=2),
            _row("G9741", "exclusion", "Patients who use hospice services any time during the measurement period"),
            _row("G0034", "exclusion", "Patients receiving palliative care during the measurement period"),
        ],
    ),
    "317": _measure(
        "317",
        claims=True,
        note=(
            "A visit measure: reported at every eligible visit for a patient 18 or older. The blood "
            "pressure must be measured at the visit by the eligible clinician, not obtained from an "
            "external source; with several readings that day, the last one counts. Not telehealth "
            "eligible (a telehealth encounter is not in the denominator). A patient with an active "
            "diagnosis of hypertension is excluded. Follow-up by reading: normal (systolic < 120 and "
            "diastolic < 80 mmHg), none required; elevated (systolic 120-129 and diastolic < 80), "
            "rescreen within 6 months with lifestyle interventions, or a referral to an alternate or "
            "primary care provider; first hypertensive reading (systolic >= 130 or diastolic >= 80, "
            "with no reading of systolic >= 130 or diastolic >= 80 in the 12 months before this "
            "visit), rescreen within 4 weeks with lifestyle interventions, or a referral; second "
            "hypertensive reading (systolic >= 130 or diastolic >= 80 at this visit AND at the most "
            "recent reading in the previous 12 months): at 130-139 or 80-89, lifestyle interventions, "
            "reassessment within 6 months and an order for a laboratory test or ECG for hypertension, "
            "or a referral; at >= 140 or >= 90, lifestyle interventions, BP-lowering medication, "
            "reassessment within 4 weeks and an order for a laboratory test or ECG, or a referral. "
            "Lifestyle interventions: weight reduction, a heart-healthy diet such "
            "as DASH, dietary sodium restriction, increased physical activity, moderation in alcohol "
            "consumption."
        ),
        rows=[
            _row("G8783", "met", "Normal blood pressure reading documented, follow-up not required"),
            _row("G8950", "met", "Elevated or Hypertensive blood pressure reading documented, AND the indicated follow-up is documented"),
            _row("G9745", "exception", "Documented reason for not screening or recommending a follow-up for high blood pressure"),
            _row("G8785", "not-met", "Blood pressure reading not documented, reason not given"),
            _row("G8952", "not-met", "Elevated or Hypertensive blood pressure reading documented, indicated follow-up not documented, reason not given"),
            _row("G9744", "exclusion", "Patient not eligible due to active diagnosis of hypertension"),
        ],
    ),
}


_MIPS_ID = re.compile(r"^\s*(?:mips\s*)?(?:quality\s*id\s*)?#?\s*(\d{1,3})\s*$", re.IGNORECASE)

HCPCS_LEVEL_II = re.compile(r"^[A-Z]\d{4}$")


def _hcpcs_rows() -> dict[str, set[str]]:
    seen: dict[str, set[str]] = {}
    for table in (MIPS_REPORTING_CODES, SPECIFIED_REPORTING_CODES):
        for measure in table.values():
            for row in measure["codes"]:
                if HCPCS_LEVEL_II.match(row["code"]):
                    seen.setdefault(row["code"], set()).add(row["meaning"])
    return seen


def _agreed_meanings(rows: dict[str, set[str]]) -> dict[str, str]:
    return {code: next(iter(meanings)) for code, meanings in rows.items() if len(meanings) == 1}


_HCPCS_ROWS = _hcpcs_rows()

HCPCS_CODES: frozenset[str] = frozenset(_HCPCS_ROWS)

HCPCS_MEANINGS: dict[str, str] = _agreed_meanings(_HCPCS_ROWS)


def _upper(code: Any) -> str:
    return code.strip().upper() if isinstance(code, str) else ""


def hcpcs_meaning(code: Any) -> str | None:
    return HCPCS_MEANINGS.get(_upper(code))


def is_mips_hcpcs(code: Any) -> bool:
    return _upper(code) in HCPCS_CODES


def normalise_mips_id(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    match = _MIPS_ID.match(value)
    return match.group(1).zfill(3) if match else None


def reporting_codes_for(mips_id: Any) -> dict[str, Any] | None:
    measure_id = normalise_mips_id(mips_id)
    entry = MIPS_REPORTING_CODES.get(measure_id) if measure_id else None
    return copy.deepcopy(entry) if entry is not None else None


def specified_reporting_codes_for(mips_id: Any) -> dict[str, Any] | None:
    measure_id = normalise_mips_id(mips_id)
    entry = SPECIFIED_REPORTING_CODES.get(measure_id) if measure_id else None
    return copy.deepcopy(entry) if entry is not None else None


REPORTING_CODES_WITHHELD = (
    "Reporting codes not shown: the measure name on this card is not CMS's 2026 title for "
    "MIPS #{id} ({title}). Check which measure this is before reporting it."
)

_DASHES = re.compile(r"[\u2010-\u2015\u2212]")


def _normalise_title(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = _DASHES.sub("-", value).replace("\u2019", "'")
    text = " ".join(text.split()).rstrip(".").strip()
    return text.casefold() or None


def attach_reporting_codes(payload: Any) -> Any:
    if not isinstance(payload, dict):
        return payload
    measures = payload.get("eligibleMeasures")
    if not isinstance(measures, list):
        return payload
    attached: list[Any] = []
    for measure in measures:
        if isinstance(measure, dict):
            codes = reporting_codes_for(measure.get("mipsId"))
            withheld = None
            if codes is not None:
                measure_id = normalise_mips_id(measure.get("mipsId"))
                title = VERIFIED_MIPS_MEASURES[measure_id][0]
                if _normalise_title(measure.get("measureName")) != _normalise_title(title):
                    codes = None
                    withheld = REPORTING_CODES_WITHHELD.format(id=measure_id, title=title)
            measure = {**measure, "reportingCodes": codes, "reportingCodesWithheld": withheld}
        attached.append(measure)
    return {**payload, "eligibleMeasures": attached}


_CATALOG_ID_BY_TITLE: dict[str, str] = {
    _normalise_title(title): measure_id for measure_id, (title, _spec) in VERIFIED_MIPS_MEASURES.items()
}

ADDED_BY_ORGANIZATION = "addedByOrganization"


def _added_titles(allowed: frozenset[str]) -> dict[str, str]:
    titles: dict[str, str] = {}
    for measure_id in allowed:
        entry = addable_measure(measure_id)
        if entry is not None:
            titles[_normalise_title(entry["title"])] = measure_id
    return titles


def _kept_under(measure: Any, allowed: frozenset[str], added_titles: dict[str, str]) -> bool:
    if not isinstance(measure, dict):
        return False
    measure_id = normalise_mips_id(measure.get("mipsId"))
    if measure_id is None or measure_id not in allowed:
        return False
    title = _normalise_title(measure.get("measureName"))
    if measure_id in VERIFIED_MIPS_MEASURES:
        titled_as = _CATALOG_ID_BY_TITLE.get(title) or added_titles.get(title)
        return titled_as is None or titled_as == measure_id
    entry = addable_measure(measure_id)
    return entry is not None and title == _normalise_title(entry["title"])


_ADDED_ROW_KEYS = (ADDED_BY_ORGANIZATION, "nursingFacilityNote", "specUrl")


def _marked(measure: dict) -> dict:
    measure_id = normalise_mips_id(measure.get("mipsId"))
    entry = org_added_entry(measure_id)
    if entry is not None:
        specified = measure_id in SPECIFIED_ADDED_MEASURE_IDS
        marked = {
            **measure,
            ADDED_BY_ORGANIZATION: True,
            "reportingCodes": specified_reporting_codes_for(measure_id) if specified else None,
            "specUrl": entry["specUrl"],
            "nursingFacilityNote": entry["nursingFacilityNote"],
        }
        if specified:
            marked["reportingCodesWithheld"] = None
        return marked
    if any(key in measure for key in _ADDED_ROW_KEYS):
        return {key: value for key, value in measure.items() if key not in _ADDED_ROW_KEYS}
    return measure


def _prior_record(payload: dict) -> dict | None:
    record = payload.get("scope")
    if not isinstance(record, dict):
        return None
    omitted, applied_at = record.get("omitted"), record.get("appliedAt")
    if isinstance(omitted, bool) or not isinstance(omitted, int) or not isinstance(applied_at, str):
        return None
    return record


def restrict_to_scope(payload: Any, scope: MipsScope | None, *, now: datetime | None = None) -> Any:
    if scope is None or not isinstance(payload, dict):
        return payload
    measures = payload.get("eligibleMeasures")
    if not isinstance(measures, list):
        return payload
    allowed = frozenset(scope.measure_ids)
    added_titles = _added_titles(allowed)
    kept = [_marked(measure) for measure in measures if _kept_under(measure, allowed, added_titles)]
    omitted = len(measures) - len(kept)
    prior = _prior_record(payload)
    if prior is not None:
        omitted += prior["omitted"]
        applied_at = prior["appliedAt"]
    else:
        applied_at = (now or datetime.now(UTC)).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    record = {
        "source": scope.source,
        "measureIds": list(scope.measure_ids),
        "omitted": omitted,
        "appliedAt": applied_at,
    }
    return {**payload, "eligibleMeasures": kept, "scope": record}
