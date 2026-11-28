# 0049 A synthetic gold set for measured accuracy

Date: 2026-11-28

Context: the owner wants published agreement numbers from a fixed set run against the live model. The
evaluation harness ([0020](0020-measured-accuracy-and-earned-autonomy.md)) scores approved notes a
practice marks as cases, but there was no set. Real notes cannot be used, so the set is synthetic and
is loaded into a dedicated evaluation practice through the public API, as a person would.

## Choices

**Where it lives.** `tools/gold_set/`: the data (`cases.json`, schema version 1), its validator, the PDF
renderer, the loader and the report. The scripts are API clients run from an operator's machine with
the backend virtual environment, so they sit beside `tools/load/`, not in `backend/app`, and import
`app.codes` (and the harness's scoring functions) only to validate and score. Tests are in
`backend/tests/tools/`. PDFs and reports go to the ignored `tools/gold_set/out/`.

**48 cases, expected answers by construction.** Each case holds the note in sections (some with
vitals, medication, laboratory or glucose tables), the visit facts, the claim as billed, the expected
claim and the shape the harness compares (`em`, `icd`, `modifiers`), the MDM elements and any total
time, and a rationale for every expected code and modifier and for each billing error. Visit codes as
billed: 21 correct, 16 one level too high, 8 one level too low, 2 two levels too high and 1 visit that
is not separately billable. The validator (`gold_checks.py`) refuses a case unless:

- every ICD-10-CM code is billable in the release for the date of service, every CPT or HCPCS code is
  in Bodha's code list, every modifier is one Bodha accepts on that line, and the date falls in the
  loaded NCCI quarters;
- the E/M code is the one its MDM gives (the middle of the three element levels, since two of three
  must be met) or its time gives when time is higher, in the family the place of service and visit
  type select; G2212 units match the Medicare thresholds (89 minutes with 99205, 69 with 99215);
- the expected claim passes the NCCI pair, add-on and unit edits, with E/M pairs bypassed only by 25
  or 57, and raises no Bodha Medicare payer flag; a telehealth visit carries exactly one of 95 or 93;
- the stored harness shape equals what `agreement.elements_of` derives, and every code and modifier
  has its rationale.

Conventions where coders could otherwise differ, so each case has one answer:

- Every MDM case is built so that reading its most debatable element one step higher or lower leaves
  the level unchanged; time cases use times inside the ranges of Bodha's E/M table, and the nursing
  facility time cases sit above both the CPT thresholds and the table's.
- Diagnoses are the conditions addressed. Status codes appear only where a use-additional-code note
  requires them (Z79.84 and Z79.4 with E11, Z87.891 with J44). Long-term drug codes without such a note
  (for example Z79.02) and external cause codes, which are voluntary, are not expected.
- G2211 is expected only on Medicare office and telehealth visits whose note states the practice is
  the continuing focal point, and never with modifier 25 for a procedure. Prolonged time uses G2212
  (Medicare). Anatomic modifiers on 20610 and 69210 are billed and expected alike.
- Telehealth follows Bodha's prompt and Medicare rules: 95 for audio-video at place of service 02 or
  10, 93 for audio-only at 10. Dates of service fall between October 2025 and November 2026 (ICD-10-CM
  2026 and 2027, before the 2027 G2211 change Bodha models).
- No real people: patients are "Synthetic Patient NN" with MRNs `SYN-00NN-ZZ`, the practice, facility
  and providers are invented, provider emails use `example.com`, and every page says it is synthetic.

**Loader.** `load_gold_set.py` signs in as the evaluation practice admin (password and TOTP secret from
the environment), refuses any practice other than `BODHA_EVAL_PRACTICE_ID`, needs an adopted signature
and level confirmation off, and creates the five synthetic providers if missing. Each case is uploaded
with its billed claim and visit facts under the file name `<date> - SYNTHETIC PATIENT - GS-NN.pdf`; the
case id in the name is the idempotency key (`/api/search`, exact file name, voided notes ignored).
After Bodha's review: if Bodha's claim at its default choices already equals the expected claim, the
note is approved as it stands; otherwise the billed codes are edited to the expected claim with the
override reason `coding_guideline`, every remaining suggestion is turned down with the same reason, the
result is checked, and the note is approved (through the compliance confirm when it sits in the
compliance lane). Then it is marked as an evaluation case. Accepting only Bodha's suggestions was
rejected: cases where Bodha suggests nothing useful could not reach their expected claim, which would
bias the set toward cases Bodha already gets right. A re-run skips loaded cases, picks up notes still
being read and refuses to mark a note approved with any other claim.

**The harness reads the billed claim as uploaded.** An evaluation run now gives the model the first
billed code set of the note (`code_sets.original_codes`), with units, instead of the latest one. A
coder's hand edit of the billed codes is a departure from Bodha recorded with a reason; reading it back
as the input handed the model the answer. This applies to every practice's evaluation set, and the
first run after the change can show a drop for cases whose billed codes had been edited.

**Provider queries are left out.** A run scores only the claim (E/M, ICD-10-CM, modifiers); a note
whose right outcome is a query has no claim to compare until the provider answers, so no query cases
are in the set.

**Report.** `report_gold_set.py` reads the latest finished run, matches results to cases by note, and
writes Markdown with the harness's own functions (`evaluation_summary`, `summarize`): Wilson intervals
for per-note rates, the per-note bootstrap for ICD-10-CM precision and recall, results by group, every
disagreement and every unscored case. It always opens with the provisional notice.

## Follows

- The expected answers have not been checked by a certified coder; numbers from this set are
  provisional until one signs off ([TECH_DEBT](../TECH_DEBT.md)).
- What the harness cannot measure: procedure lines, add-on codes (G2211, G2212), units and place of
  service are not scored (scored since [0055](0055-evaluations-score-claim-lines.md)). Bodha's suggested claim cannot remove a visit code or a modifier, so GS-26
  (modifier 25 unsupported) can only disagree; the report shows results with and without it.
- CPT 99417 is not in Bodha's code list (the CMS fee schedule lists it as not valid for Medicare), so a
  commercial claim carrying it cannot be approved; the set uses Medicare G2212 instead (99417 added in
  [0054](0054-prolonged-service-99417.md)).
- Found while building the set, not changed here: the NCCI claim check treats RT or LT on a procedure as
  bypassing its edit with an E/M code that lacks modifier 25; blind audit samples freeze Bodha's
  suggestion from the latest billed codes, so they share the leak fixed above for evaluation runs; Bodha's
  E/M table gives 50 minutes for 99306 and 20 for 99308, where the CPT 2023 nursing facility thresholds
  are 45 and 15. The first two are fixed in [0052](0052-ncci-bypass-by-relationship.md) and
  [0053](0053-blind-audits-read-the-claim-as-uploaded.md). The nursing facility times are kept: they match
  the more recent AMA and AAPC tables, and a certified coder will confirm.
