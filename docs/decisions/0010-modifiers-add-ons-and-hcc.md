# 0010 Modifiers, add-on codes, CPT-only claims, critical care and risk adjustment

Context: the E/M answer already named modifiers and add-on codes, but they were dropped; a claim
billed with CPT codes only sent every note to a coder for the diagnoses it lacked; critical care and
same-day admission and discharge were missing from the E/M families; the legacy app showed HCC
captured, missed and suspected with a model-estimated RAF; MIPS showed which measures were met.

## Modifiers and add-on codes

- The E/M answer gives each modifier with the code it belongs on (`""` for the visit code) and each
  add-on code with a name, a reason and evidence (`ModifierSuggestion`, `AddOnSuggestion`). Stored
  reports that hold bare strings still read: a string becomes an item with no reason.
- Bodha adds only modifiers from `codes/modifiers.py`: `VISIT_MODIFIERS` on an E/M code,
  `PROCEDURE_MODIFIERS` on any other code. 59 and the X modifiers never go on an E/M code (CPT
  defines 59 for services other than E/M; 25 is the E/M modifier). Add-on codes must pass
  `is_known_cpt`. Anything else is a `review` suggestion with no code before or after, so it never
  reaches the claim and never blocks approval.
- A supported modifier is a `modifier` suggestion, action `add`, from the target code to the code
  with the modifier. A visit modifier targets the suggested level when the level changes and uses the
  key `modifier:<modifier>` so a decision survives a level change; the claim puts it on whichever
  E/M code the claim ends up with. A procedure modifier uses `modifier:<code>:<modifier>`.
- A supported add-on code is a `code_review` suggestion, action `add`, key `addon:<code>`.
- Both default to `accept`; keep leaves the claim as billed. A modifier or add-on already billed is
  not suggested again, and the claim keeps one line per code with at most four modifiers.
- Both are code changes, so the note goes to a coder ("Modifier missing", "Add-on code missing").

## CPT-only claims

`routing.place` takes `billed_diagnoses`, true when the billed list has any ICD-10-CM code
(`has_diagnosis_codes`). When it is false, documented supported diagnoses are added to the claim by
default and do not count as code changes, so the note can be approved ("Diagnoses added from the
note"). Diagnoses that need detail stay questions for the provider. Legacy skipped the diagnosis
comparison in that case.

## E/M families

- Same-day admission and discharge, hospital inpatient or observation: 99234 straightforward or low
  MDM or 45 minutes, 99235 moderate or 70, 99236 high or 85 (AMA, *CPT 2023 E/M descriptors and
  guidelines*). The stay is 8 hours or more and ends on the admission date; under 8 hours is an
  initial code only (CMS MLN006764, May 2026).
- Critical care, any setting: 99291 for 30-74 minutes, once per date; 99292 for each additional 30
  minutes, first paid by Medicare at 104 minutes (CMS MLN006764, May 2026). 99292 is an add-on of
  the family, not a level, so it is not an E/M level code and is suggested through add-on codes.

## Risk adjustment

- Optional check `hcc`, off by default; it needs the diagnosis check (`icd`). Old practices read
  the new check as off.
- The model lists only suspected conditions (clinical indicators without a diagnosis) with a
  compliant, non-leading query. It never names categories, weights or scores.
- Categories and scores are deterministic, from the CMS-HCC V28 payment year 2027 initial model
  software (Python package `CMS_HCC_v28_2027_T1_initial_package_v2`), vendored as two gzip TSV files
  with a checksummed manifest in `backend/app/codes/data`. Dates of service in year N feed payment
  year N+1.
- Captured: a payment HCC from both the billed and the documented codes. Missed: documented, not
  billed. Not supported: billed with nothing documented in its hierarchy. Suspected conditions that
  map to a payment HCC and are neither billed nor documented become `diagnosis` questions (`ask`).
- The score is the disease part of the community, non-dual score: HCC relative factors after
  hierarchies, the disease interactions and the payment HCC count, for the aged segment (65 or older)
  or the disabled segment (under 65). It leaves out the demographic factors, normalisation and the
  MA coding pattern adjustment, so it compares the billed and the documented codes; it is not the
  member's RAF. No age, no score.
- The summary is one `diagnosis` suggestion with key `hcc` and action `info`, shown in a Risk
  adjustment tab; no new suggestion kind, no migration.

## MIPS

Each eligible measure carries `status`: `met` (the note documents what the measure asks for, so the
macro has no placeholder), `missing`, or `not_applicable` (a documented exception). A `met` answer
whose macro still holds a placeholder is stored as `missing`.

## Follows

- The PY2027 initial mapping covers ICD-10-CM codes valid in FY2025 and FY2026; FY2027 codes map
  to nothing until the midyear files are vendored. Payment years other than 2027 show "No CMS-HCC
  model".
- MCE age edits use the age the note states, not the age on February 1 of the payment year.
- Units were not on the claim: an add-on billed more than once (96127 twice, 99292 twice) was added
  once and the coder set the units. Superseded by [0014](0014-units-and-medicare-national-estimates.md).
- Prompt version 2026.11.2.

Amendment (2026-11-27):

- The patient facts carry the date of birth when the note states it (`patient.birth_date`, YYYY-MM-DD,
  prompt version 2026.11.4). The analysis keeps it on `notes.patient_birth_date` when the note has none
  and it is not after the date of service.
- HCC age edits and the segment use the age on 1 February of the payment year when the birth date is
  known, as the CMS-HCC model does. Without it they use the age in the note, and the risk summary says
  so (`age_from: note`, shown as "Age from note").
- On 2026-11-27 the CMS page *2027 Model Software/ICD-10 Mappings* lists only the initial model software
  and the initial ICD-10-CM mappings; no PY2027 midyear or final mapping is published yet, so FY2027
  codes still map to no HCC.
