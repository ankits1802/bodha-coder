from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from app.ai.prompts.mips_practice import practice_scope_line, render_practice_measures
from app.ai.prompts.mips_titles import measure_heading, with_measure_headings
from app.codes.mips_catalog import SPECIFIED_ADDED_MEASURE_IDS, VERIFIED_MIPS_MEASURES, addable_measure
from app.codes.mips_scope import MipsScope

__all__ = ["CMS_INVERSE_MEASURE_SENTENCE", "render_scope_addendum"]

CMS_INVERSE_MEASURE_SENTENCE = (
    "This is an inverse measure which means a lower calculated performance rate for this "
    "measure indicates better clinical care or control."
)

_SCOPE_ADDENDUM = """
# THIS PRACTICE'S MEASURE LIST

The practice reports ONLY the measures listed here:
{{measures}}

- Suggest NO measure that is not listed here, even when the patient meets its denominator. Leave it out of
  eligibleMeasures entirely, and do not name it in a rationale, a macro or the fallbackMessage.
- Being listed is NEVER a reason to suggest a measure. The PRIMARY RULE (DENOMINATOR-FIRST) and each measure's
  exclusions above still decide: suggest a listed measure only when the note clearly meets its denominator and no
  documented exclusion applies.
- Name a listed measure exactly as its heading does: the same three-digit CMS quality ID and the same CMS title.
- If no listed measure meets its denominator, answer with the FALLBACK above.
"""

_ADDED_MEASURES_ADDENDUM = """
# PRACTICE-ADDED CMS MEASURES

This practice's list also names the CMS 2026 quality measures below. Each is given only as CMS publishes it: its
three-digit CMS quality ID, its CMS title, CMS's own description and, where CMS marks the measure as inverse, CMS's
sentence saying so. They have no heading, denominator, exclusion or macro in this prompt, and they ARE allowed
under this list: the PRIMARY RULE's "suggest no measure that is not listed" and the list above do not exclude
them.
{{added}}

- Suggest one of these ONLY when the note shows that the patient fits its CMS description: the patients the
  description counts, by age, sex, diagnosis or history. Whatever else the description names for those patients
  (usually after "who" or "whose") is what the measure checks for: it is never a reason to leave the measure out,
  and never something to write as done or as not done.
- For an inverse measure (one whose entry carries CMS's inverse-measure sentence), what it checks for is an outcome
  to avoid (a lower rate is better), never care the patient should have had or should receive. Never write its
  macro as if the patient needs it.
- Being listed is NEVER a reason to suggest one of these. DENOMINATOR-FIRST still decides: when the note does not
  clearly show that the patient fits the description, leave the measure out.
- Name it exactly as it is listed here: mipsId is "MIPS #" and its three-digit ID, and measureName is its CMS title
  exactly as written above.
- Its macro is documentation prompts only: one or more [PLACEHOLDER: ...] slots, each naming what the clinician
  should record for that measure, following the THREE RULES above: no code of any kind, and nothing the note does
  not document.
- exceptionExclusion is null for these measures.
"""

_SPECIFIED_MEASURES_ADDENDUM = """
# PRACTICE-ADDED MEASURES WITH GUIDANCE

This practice's list also names the CMS 2026 quality measures below, for which this review carries CMS's 2026
specification. Each has a heading, a denominator, exclusions and a macro here, exactly like the measures in Step 2
above, and they ARE allowed under this list: the PRIMARY RULE's "suggest no measure that is not listed" and the
list above do not exclude them. The THREE RULES, the PRIMARY RULE (DENOMINATOR-FIRST), Step 2's exclusion rule and
Step 3 apply to them exactly as to the measures above, with two differences: where a measure's block below gives
its own instruction (for example what to write in exceptionExclusion), that instruction wins; and each is named
exactly as its heading BELOW does: mipsId is "MIPS #" and its three-digit ID, and measureName is its CMS title
exactly as written in its heading. Being listed is NEVER a reason to suggest one.
{{specified}}
"""

_SPECIFIED_047 = """
### {{measure 047}}
- Denominator: patients aged 65 or older on the date of the encounter with a qualifying visit. CMS's qualifying
  visits include office, home, nursing facility and telehealth visits; a visit in the emergency department is NOT
  in this denominator.
- Trigger: age 65 or older AND the setting is not "emergency"
- Exclusion: hospice services at any time during the measurement period: the only exclusion.
- Fill the placeholder below only from an advance care plan, surrogate decision maker or advance care planning
  discussion the note itself documents. Never infer one from the diagnoses or the setting, and never write that a
  plan exists or that one was discussed otherwise.
- Macro: "Advance care plan: [PLACEHOLDER: record the advance care plan or surrogate decision maker documented in
  the medical record, or that advance care planning was discussed and the patient did not wish or was not able to
  name a surrogate decision maker or provide an advance care plan]."
- Exceptions: none; CMS lists no denominator exception for this measure.
"""

_SPECIFIED_126 = """
### {{measure 126}}
- Denominator: patients aged 18 or older on the date of the encounter with type 1, type 2 or other specified
  diabetes, seen IN PERSON. CMS's qualifying visits include office, home and nursing facility visits; emergency
  department and hospital inpatient visits are not among them. CMS's diagnosis list does not include gestational
  diabetes or diabetes due to an underlying condition or induced by a drug or chemical. This measure is NOT
  telehealth eligible: a telehealth visit is not in its denominator.
- Trigger: the note documents type 1, type 2 or other specified diabetes AND the patient is aged 18 or older AND
  the setting is not "telehealth", "emergency" or "inpatient"
- Exclusion: CMS excludes the patient only when the CLINICIAN documents that the patient is not an eligible
  candidate for a lower extremity neurological exam. CMS's examples: a bilateral amputee; a condition that would
  not allow the patient to respond accurately to a neurological exam (dementia, Alzheimer's disease and the like);
  previously documented diabetic peripheral neuropathy with loss of protective sensation. A diagnosis alone does
  not remove this measure: when the note names one of CMS's examples without that determination, still suggest
  the measure, and say in exceptionExclusion that CMS excludes the patient if the clinician documents that they are
  not an eligible candidate for the exam, naming the diagnosis and where the note shows it.
- Macro: "Lower extremity neurological exam: [PLACEHOLDER: record the 10-g monofilament result plus at least one of
  vibration with a 128-Hz tuning fork, pinprick sensation, ankle reflexes or vibration perception threshold, and
  its date (this encounter or within the past 12 months)]."
- Exceptions: a documented medical reason for not performing the lower extremity neurological exam
"""

_SPECIFIED_155 = """
### {{measure 155}}
- Denominator: patients aged 65 or older on the date of the encounter with a HISTORY OF FALLS (two or more falls in
  the past year, or any fall with injury in the past year; the patient's own report is enough) and a qualifying
  visit. CMS's qualifying visits include office, home, nursing facility and telehealth visits; emergency department
  and hospital inpatient visits are not among them.
- Trigger: age 65 or older AND the note documents two or more falls or a fall with injury (for example "recurrent
  falls", "repeated falls", or an injury from a fall) AND the setting is not "emergency" or "inpatient". The note
  seldom dates a fall: an undated history is enough to suggest the measure, but leave the measure out when the note
  dates the falls or the injury to more than a year before the dateOfService, and do not say in
  eligibilityRationale that the falls were in the past year: the macro's first placeholder is where the clinician
  records that. A fall-risk statement, or a "history of falls" that gives neither the number of falls nor an
  injury, does NOT meet the denominator: leave the measure out.
- Exclusion: hospice services at any time during the measurement period: the only exclusion.
- Macro: "Falls in the past year: [PLACEHOLDER: record the number of falls in the past year and any injury]. Falls
  plan of care: [PLACEHOLDER: document the balance, strength and gait training or instructions, a referral to an
  exercise program that includes balance, strength or gait training, or a referral to physical therapy]."
- Exceptions: the patient is not ambulatory: bed ridden, immobile, confined to a chair, wheelchair bound, dependent
  on a helper pushing the wheelchair, independent in a wheelchair, or needing minimal help in a wheelchair
"""

_SPECIFIED_238 = """
### {{measure 238}}
- CMS: This is an inverse measure which means a lower calculated performance rate for this measure indicates
  better clinical care or control. What it counts (two or more ORDERS for high-risk medications from the same drug
  class) is an outcome to avoid, never care the patient should have had or should receive. Never write the macro
  as if the patient needs a high-risk medication.
- Denominator: patients aged 65 or older on the date of the encounter with a qualifying visit. CMS's qualifying
  visits include office, home, nursing facility, nursing facility discharge and telehealth visits.
- Trigger: age 65 or older
- Exclusion: hospice services or palliative care at any time during the measurement period.
- What CMS counts: the patient was ordered two or more high-risk medications from the same drug class, on different
  dates of service in the measurement period. CMS: "If the patient had a high-risk medication previously
  prescribed by another provider, they would not be counted towards the numerator unless the submitting provider
  also ordered a high-risk medication for them from the same drug class." Each class below (one row of CMS's
  tables) is its own drug class (a class that names one medication is a class of one), and a Table 2 or Table 3
  medication is high risk only beyond its criterion. Two submission criteria: (1) Tables 1-3, the one CMS scores
  performance on; (2) Table 4, antipsychotics and benzodiazepines, except for appropriate diagnoses (an
  antipsychotic with schizophrenia, schizoaffective disorder or bipolar disorder; a benzodiazepine with a seizure
  disorder, rapid eye movement sleep behavior disorder, benzodiazepine withdrawal, ethanol withdrawal or severe
  generalized anxiety disorder).
  Table 1 (high risk at any dose or duration): anticholinergics, first-generation antihistamines:
  brompheniramine, chlorpheniramine, cyproheptadine, dimenhydrinate, diphenhydramine (oral), doxylamine,
  hydroxyzine, meclizine, promethazine, triprolidine; anticholinergics, anti-Parkinson agents: benztropine (oral),
  trihexyphenidyl; antispasmodics: atropine (not ophthalmic), chlordiazepoxide-clidinium, dicyclomine, hyoscyamine,
  scopolamine; antithrombotics: dipyridamole (oral, not extended release); cardiovascular, alpha agonists,
  central: guanfacine; cardiovascular, other: nifedipine (not extended release); central nervous system,
  antidepressants: amitriptyline, amoxapine, clomipramine, desipramine, imipramine, nortriptyline, paroxetine;
  central nervous system, barbiturates: butalbital, phenobarbital, primidone; central nervous system,
  vasodilators: ergoloid mesylates; central nervous system, other: meprobamate; endocrine system, estrogens with
  or without progestins (oral and topical patch products only): conjugated estrogen, esterified estrogen,
  estradiol, estropipate; endocrine system, sulfonylureas, long-duration: glimepiride, glyburide; endocrine
  system, desiccated thyroid: desiccated thyroid; endocrine system, megestrol: megestrol; nonbenzodiazepine
  hypnotics: eszopiclone, zaleplon, zolpidem; pain medications, skeletal muscle relaxants: carisoprodol,
  chlorzoxazone, cyclobenzaprine, metaxalone, methocarbamol, orphenadrine; pain medications, meperidine:
  meperidine; pain medications, other: indomethacin, ketorolac (oral and parenteral).
  Table 2 (high risk only over 90 days' cumulative supply): anti-infectives, other: nitrofurantoin, nitrofurantoin
  macrocrystals-monohydrate.
  Table 3 (high risk only above an average daily dose): cardiovascular, other: digoxin above 0.125 mg a day;
  tertiary tricyclic antidepressants, alone or in a combination product: doxepin above 6 mg a day.
  Table 4: antipsychotics, first (conventional) and second (atypical) generation: aripiprazole, aripiprazole
  lauroxil, asenapine, brexpiprazole, cariprazine, chlorpromazine, clozapine, fluphenazine, haloperidol,
  iloperidone, loxapine, lurasidone, molindone, olanzapine, paliperidone, perphenazine, pimavanserin, pimozide,
  quetiapine, risperidone, thioridazine, thiothixene, trifluoperazine, ziprasidone; benzodiazepines, long, short
  and intermediate acting: alprazolam, chlordiazepoxide, clobazam, clonazepam, clorazepate, diazepam, estazolam,
  lorazepam, midazolam, oxazepam, temazepam, triazolam.
- A medication list is NOT a record of who ordered what, or when. Never write that a medication was ordered or
  prescribed, by whom, on what date or how often, unless the note itself says so, and never call one
  inappropriate.
- Macro: "High-risk medications in older adults: [PLACEHOLDER: record each high-risk medication from the same drug
  class ordered for this patient on different dates of service during the measurement period, with its date and
  whether you ordered it or another provider prescribed it, or that none was ordered]."
  (If the note's medication list names a medication from Tables 1-4, add one sentence after the placeholder: "On
  the medication list: " then each such medication's name as the list gives it, a dash and its class as the tables
  above name it (for a Table 2 or Table 3 medication, its class followed by "high risk only" and its criterion,
  for example "nitrofurantoin - anti-infectives, other, high risk only over 90 days' cumulative supply"), separated
  by semicolons and ending with a full stop. Never say whether a criterion is met.)
- Exceptions: none; CMS lists no denominator exception for this measure.
"""

_SPECIFIED_317 = """
### {{measure 317}}
- Denominator: every visit, IN PERSON, for a patient aged 18 or older at the start of the performance period.
  CMS's qualifying visits include office, home, nursing facility, nursing facility discharge and emergency
  department visits; of hospital care CMS lists only a same-day admission and discharge, so a hospital inpatient
  visit is not in this denominator. This measure is NOT telehealth eligible: a telehealth visit is not in its
  denominator.
- Trigger: age 18 or older AND the setting is not "telehealth" or "inpatient"
- Exclusion: an active diagnosis of hypertension before this encounter: leave the measure out when the note
  documents hypertension.
- The reading must be one the clinician measured at this visit, never one from another source: fill the first
  placeholder below only from a blood pressure the note records as taken at this visit. Never write a
  classification, or that a follow-up is or is not needed.
- Macro: "Blood pressure screening at this visit: [PLACEHOLDER: record the systolic and diastolic blood pressure
  measured at this visit, the last reading if there were several]. Follow-up if elevated or hypertensive:
  [PLACEHOLDER: document the recommended follow-up for the reading, or record that the reading is normal and no
  follow-up is required]."
- Exceptions: a documented medical reason for not screening (for example an urgent or emergent situation where
  delaying treatment would jeopardize the patient's health), or a documented patient reason for not screening or
  for not ordering the follow-up (for example the patient refuses)
"""

_SPECIFIED_BLOCKS: Mapping[str, str] = MappingProxyType(
    {
        "047": _SPECIFIED_047,
        "126": _SPECIFIED_126,
        "155": _SPECIFIED_155,
        "238": _SPECIFIED_238,
        "317": _SPECIFIED_317,
    }
)


def render_scope_addendum(scope: MipsScope) -> str:
    built_in = [
        f"- {measure_heading(measure_id)}" for measure_id in scope.measure_ids if measure_id in VERIFIED_MIPS_MEASURES
    ]
    added = [measure_id for measure_id in scope.measure_ids if addable_measure(measure_id) is not None]
    listed = built_in + [_added_scope_line(measure_id) for measure_id in added]
    listed += [practice_scope_line(definition) for definition in scope.practice_measures]
    rendered = _SCOPE_ADDENDUM.replace("{{measures}}", "\n".join(listed) or "- none")
    described = [measure_id for measure_id in added if measure_id not in SPECIFIED_ADDED_MEASURE_IDS]
    specified = [measure_id for measure_id in added if measure_id in SPECIFIED_ADDED_MEASURE_IDS]
    if described:
        lines = "\n".join(_added_entry_lines(measure_id) for measure_id in described)
        rendered += _ADDED_MEASURES_ADDENDUM.replace("{{added}}", lines)
    if specified:
        blocks = "".join(_SPECIFIED_BLOCKS[measure_id] for measure_id in specified)
        rendered += _SPECIFIED_MEASURES_ADDENDUM.replace("{{specified}}", blocks)
    return with_measure_headings(rendered) + render_practice_measures(scope.practice_measures)


def _added_scope_line(measure_id: str) -> str:
    where = (
        "PRACTICE-ADDED MEASURES WITH GUIDANCE"
        if measure_id in SPECIFIED_ADDED_MEASURE_IDS
        else "PRACTICE-ADDED CMS MEASURES"
    )
    return f"- {measure_heading(measure_id)} (added by this practice: see {where} below)"


def _added_entry_lines(measure_id: str) -> str:
    entry = addable_measure(measure_id)
    if entry is None:
        raise ValueError(f"MIPS #{measure_id} is not an addable 2026 CMS measure.")
    description = " ".join(entry["description"].split())
    lines = f"- {measure_heading(measure_id)}\n  CMS description: {description}"
    if entry["isInverse"]:
        lines += f"\n  CMS: {CMS_INVERSE_MEASURE_SENTENCE}"
    return lines
