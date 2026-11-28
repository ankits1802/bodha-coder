# 0019 NCCI edits, payer rules and claim lines

Context: coders and billers need to see, before a claim leaves, which codes CMS will not pay
together, which units are over the limit, and which payer policies put a line at risk. Billers
also need claim lines they can key or import into an 837P without retyping.

## NCCI data

- Source: CMS Medicare NCCI, practitioner tables for 2026 Q4, retrieved 2026-11-27.
  - PTP edits v323r0, effective 2026-10-01, posted 2026-09-02, four parts from the
    [PTP page](https://www.cms.gov/medicare/coding-billing/national-correct-coding-initiative-ncci-edits/medicare-ncci-procedure-procedure-ptp-edits):
    `medicare-ncci-2026q4-practitioner-ptp-edits-ccipra-v323r0-f1.zip` to `-f4.zip` (77 MB of zips,
    2,637,645 edits; the counts match the page).
  - Add-on code edits effective 2026-10-01 from the
    [add-on page](https://www.cms.gov/medicare/coding-billing/national-correct-coding-initiative-ncci-edits/medicare-ncci-add-code-edits):
    `add-code-edits-medicare-effective-10012026.zip` (`AOC_V2026Q4-F-MCR.txt`, 9,003 edits).
  - Practitioner services MUE tables for 2025 Q4, 2026 Q1, Q2 and Q3 from the
    [MUE archive](https://www.cms.gov/medicare/coding-billing/national-correct-coding-initiative-ncci-edits/medicare-ncci-medically-unlikely-edit-mue-archive)
    and 2026 Q4 from the
    [MUE page](https://www.cms.gov/medicare/coding-billing/national-correct-coding-initiative-ncci-edits/medicare-ncci-medically-unlikely-edits-mues)
    (`medicare-ncci-<year>-q<n>-practitioner-services-mue-table.zip`, about 15,200 codes each).
- `tools/fetch_ncci.py` downloads the zips (or reads them from `--sources`), checks every row,
  and writes gzip TSV artefacts and `ncci_practitioner.meta.json` with each source URL, zip size,
  SHA-256 of each zip, of each source file and of each artefact (compressed and uncompressed),
  row counts and the transform. `codes/ncci.py` refuses an artefact whose checksum, header or row
  count differs, and a manifest whose MUE quarters do not cover the served dates.
- Kept columns: PTP column 1, column 2, effective date, deletion date (blank when CMS shows `*`),
  modifier indicator; add-on code, primary code (`CCCCC` where the contractor defines them), edit
  type, effective and deletion dates (converted from year and day of year); MUE code, value and
  adjudication indicator (MAI). Edit rationales, MUE rationales and descriptors are dropped.
- Served dates: 2025-10-01 (the first day of ICD-10-CM FY 2026, the oldest release Bodha loads)
  through 2026-12-31 (the end of the quarter). PTP and add-on edits deleted before 2025-10-01 are
  dropped (1,749,750 PTP edits kept), and one MUE table per quarter is kept so a date of service
  uses its own quarter's limits (96127 is 3 in 2025 Q4 and 4 in 2026 Q4). Other dates are refused
  (`NcciUnavailable`); the claim checks then say the quarter is not loaded. A new quarter is a
  rerun of the tool.
- Size: 4.8 MB for the PTP artefact and about 0.2 MB for the rest, so the artefacts are in git
  (the limit set for this was about 15 MB). In memory the PTP table is one sorted text block of
  about 42 MB, searched by bisection, loaded on first use; parsing every edit into objects would
  take several hundred MB.
- Licence: CMS publishes NCCI behind the AMA CPT licence page. The artefacts hold codes only, no
  descriptors, like the CPT code list and RVUs already vendored (0002, 0014). The owner confirms
  that this is acceptable in the public repository; if not, the artefacts leave git and the
  deployment runs `tools/fetch_ncci.py`, and the loader moves to `contentSha256` (the
  uncompressed hash, already in the manifest), because gzip output can differ between zlib builds.

## Reading the edits

- Deletion date: the last date of service the edit applies to, so an edit applies when
  effective ≤ date of service ≤ deletion. This differs from the "date of service before the
  deletion date" first proposed, and the data shows why: every deletion that is not on its
  effective date falls on a quarter's last day (20231231, 20260630 and so on), and the 668 pairs
  that were deleted and re-added start again the very next day (0007U/0328U deleted 20230630,
  re-added 20230701). Reading the deletion date as exclusive would drop the edit on that last day.
- Indicator 9 (98,971 rows) is used for edits whose deletion date equals their effective date
  ("There is no active edit for this PTP code pair", MLN
  [How to use the Medicare NCCI tools, chapter 2](https://www.cms.gov/outreach-and-education/mln/educational-tools/mln901346-how-to-use-the-medicare-ncci/ncci-medicare/chapter_2_using_the_ncci_tools));
  those rows are not kept, and neither are add-on edits deleted on their effective date.
- PTP-associated modifiers, from the
  [2026 Medicare NCCI Policy Manual, chapter I, section E](https://www.cms.gov/files/document/01-chapter1-ncci-medicare-policy-manual-2026-final.pdf):
  anatomic E1-E4, FA, F1-F9, TA, T1-T9, LT, RT, LC, LD, RC, LM, RI; global surgery 24, 25, 57,
  58, 78, 79; other 27, 59, 91, XE, XS, XP, XU. 22, 76 and 77 do not bypass. The manual allows
  the modifier on either code ("both services may be reported with the NCCI PTP-associated
  modifier"), so Bodha accepts 59, X{EPSU}, 27, 58, 78, 79 and 91 on either line, 24, 25 and 57
  only on the E/M line, and an anatomic modifier only when the other line does not carry the same
  one (RT with LT bypasses, RT with RT does not). Indicator 0 is never bypassed. The result says
  which modifier bypassed it; whether its use is clinically justified stays with the coder.
  Amended 2026-11-28 by [0050](0050-ncci-bypass-by-relationship.md): a pair with an E/M code is
  bypassed only by 24, 25 or 57 on the E/M line, and an anatomic modifier bypasses a pair of
  procedures only when both lines carry one and they differ.
- MUE: MAI 1 is per claim line, MAI 2 and 3 per date of service (the MLN chapter above), so MAI 1
  compares each line's units and MAI 2 and 3 the sum of the claim's lines for the code.
- Add-on edits: a type 1 add-on (every primary listed) billed without any listed primary is an
  edit. Types 2 and 3 leave primaries to the contractor and are not flagged. G2211's primaries
  gain the home or residence visits 99341-99350 from 2026-01-01 in the CMS file, which the
  payer rule below relies on.
- These are Medicare tables. Medicaid NCCI tables differ and are not loaded.

## Payer rules

Advisory only: a flag never changes a suggestion, the lane or the claim. Each rule is keyed by
plan type (`medicare`, `medicare_advantage`, `medicaid`, `commercial`) and, where named, a payer
family read from the payer's name. Severity `denial` means CMS or the payer states the line is not
paid as billed, `risk` a likely denial, adjustment or loss, `reminder` a rule Bodha cannot check
from one claim.

| Rule | Plan | Check | Source |
|---|---|---|---|
| `telehealth_place` (risk) | Medicare | modifier 95 with a place other than 02, 10, 19 or 22 | Since CY 2024 telehealth uses POS 02 (not the home, facility rate) or 10 (the home, non-facility rate) and no longer the in-person POS with 95; 95 stays for a clinician in the hospital with the patient at home (CY 2024 PFS final rule, [88 FR 78875-78876](https://www.govinfo.gov/content/pkg/FR-2023-11-16/html/2023-24184.htm); CMS [telehealth FAQ](https://www.cms.gov/files/document/telehealth-faq-updated-10-09-2026.pdf) A8). The request read "needs 95/93 or the right POS"; CMS does not require 95 with POS 02 or 10, so Bodha flags the old pairing instead |
| `audio_only_place` (denial) | Medicare | modifier 93 or FQ with a place other than 10, 19 or 22 | Audio-only applies to a patient in their home, reported with 93 (FQ for RHC and FQHC), [42 CFR 410.78(a)(3)](https://www.ecfr.gov/current/title-42/section-410.78) |
| `home_telehealth_ended` (risk) | Medicare | POS 10 after 2027-12-31 | The home as originating site, the practitioner list and audio-only run "ending on December 31, 2027", Consolidated Appropriations Act, 2026, [Pub. L. 119-75 §6209](https://www.govinfo.gov/content/pkg/PLAW-119publ75/html/PLAW-119publ75.htm). Behavioral health telehealth from the home continues; Bodha cannot tell it from the claim, hence risk |
| `complexity_with_25` (denial) | Medicare | through 2026 G2211, from 2027 modifier B1, with an E/M carrying 25, and no service of CR 13705 attachment 1 on the claim (from 2025) | G2211 is not paid with a modifier 25 visit except beside an AWV, IPPE, vaccine administration or Part B preventive service ([MLN MM13473](https://www.cms.gov/files/document/mm13473-how-use-office-and-outpatient-evaluation-and-management-visit-complexity-add-code-G2211.pdf); [CR 13705, R13015OTN](https://www.cms.gov/files/document/r13015otn.pdf), attachment 1: 71271, 76706, 76977, 77063, 77067, 77078, 77080, 77081, 77085, 90460, 90461, 90471-90474, 96156, 96158, 96159, 96164, 96165, 96167, 96168, 97802-97804, 99406, 99407, 99497, 99498, G0101, G0102, G0104-G0106, G0108, G0109, G0120, G0121, G0124, G0130, G0136, G0141, G0270, G0271, G0296, G0402-G0405, G0438, G0439, G0442-G0447, G0473, G0513, G0514, P3001, Q0091). Home or residence visits join from 2026-01-01 ([CR 14447, R13753CP](https://www.cms.gov/files/document/r13753cp.pdf), Claims Processing Manual 12 §30.6.19). From 2027 G2211 becomes modifier B1 on the E/M with the same modifier 25 policy (CY 2027 PFS final rule, [91 FR 71097-71104](https://www.govinfo.gov/content/pkg/FR-2026-11-09/html/2026-22743.htm)) |
| `g2211_replaced` (denial) | Medicare | G2211 on a claim dated 2027 or later | CY 2027 PFS final rule, 91 FR 71097-71104: "the code will no longer be payable" once B1 replaces it |
| `level_downcode_risk` (risk) | commercial, Cigna | 99204, 99205, 99214, 99215, 99244 or 99245 from 2025-10-01 when every diagnosis on the claim is a symptom (R) or a status or encounter code (Z), patient not under one | Cigna "may adjust the E/M CPT code 99204-99205, 99214-99215, 99244-99245 to a single level lower when the encounter criteria on the claim does not support the higher-level E/M CPT code reported", excluding children under one, certain transplants and complex conditions, and behavioral health providers ([Cigna R49](https://static.cigna.com/assets/chcp/secure/pdf/resourceLibrary/clinReimPolsModifiers/R49_Evaluation_and_Management_Coding_Accuracy.pdf), effective 2025-10-01). Cigna screens claim data and targets outlier providers ([Cigna provider news, 2025-11-18](https://providernewsroom.com/cigna-healthcare/new-reimbursement-policy-for-professional-evaluation-and-management-services-claims-effective-october-1-2025/)); its algorithm is not published, so "no disease diagnosis on the claim" is Bodha's proxy. Maryland ordered Cigna to stop automatic reductions (MIA-2026-03-009, 2026-03-13); Bodha does not know the plan's state. The flag reads "Likely downcode, document MDM" |
| `audio_only_risk_adjustment` (risk) | Medicare Advantage | an E/M with 93 or FQ from 2026-01-01 | "For CY 2027, CMS is finalizing the proposal to exclude diagnoses identified as resulting from audio-only services using modifiers '93' or 'FQ'", and CY 2027 payments use 2026 dates of service ([CY 2027 Rate Announcement](https://www.cms.gov/files/document/2027-announcement.pdf)). The request said "from 2027"; that is the payment year, so the rule starts with 2026 dates of service. The exclusion applies when no other line on the record is risk-adjustment eligible; Bodha flags the audio-only visit and leaves that judgement to the coder |
| `initial_visit_repeated` (denial) | every plan | 99304-99306 at POS 31 or 32 when Bodha holds an earlier initial visit at POS 31 or 32 for the same patient by a provider of the same specialty (or with no specialty recorded), with no discharge (99315, 99316) dated from that visit to this one | An initial visit is one where the patient "has not received any professional services from the physician or other NPP of the same specialty who belongs to the same group practice during the stay" ([Claims Processing Manual 12 §30.6.13](https://www.cms.gov/regulations-and-guidance/guidance/manuals/downloads/clm104c12.pdf)); CPT's nursing facility guidelines define an initial service the same way, so it is not limited to Medicare. The same patient is the same practice and patient name (order, case and initials ignored) and, when both notes have one, the same date of birth. The history is Bodha's own notes: the code of each note's final code set once approved, otherwise its latest billed set. A stay that began outside Bodha is not seen. The flag carries the earlier date (`earlier`) |
| `nursing_incident_to` (reminder) | Medicare | an E/M at POS 31 or 32 by a provider who is not an MD or DO and has a supervising physician on file | "'Incident to' E/M visits, provided in a facility setting, are not payable under the Physician Fee Schedule" (Claims Processing Manual 12 §30.6.13.E; [Benefit Policy Manual 15 §60](https://www.cms.gov/regulations-and-guidance/guidance/manuals/downloads/bp102c15.pdf)). A claim does not say it is billed incident to, so a supervised non-physician in a facility is the signal |

- Medicaid has no rule yet; commercial payers other than Cigna have none. `initial_visit_repeated`
  is the exception: it reads Bodha's history rather than the payer and is checked with or without a
  payer (amended 2026-11-27; it replaced the `nursing_initial_once` reminder).
- The practice payer list (`services/payers.py`) offers `commercial`, `medicare`, `medicaid` and
  `other`. `medicare_advantage` reaches the rules only once that list offers it; `other` maps to
  no plan and gets no payer flags.
- Not handled: modifiers BB and BC (third-party telehealth platforms and incident-to telehealth,
  required from 2027-01-01, no payment effect) and FR (virtual direct supervision).

## Claim lines

- One claim per approved, not yet exported note, from its final code set; up to 500 per request.
  The existing export still marks notes exported; claim lines do not.
- Diagnoses take the letters A to L in claim order and are written without the period, as the
  X12 837P (005010X222A1) carries them. More than 12 is refused with the note id, as is a claim
  without a procedure or a diagnosis.
- Pointers (amended 2026-11-27): in note review the coder links up to four of the claim's
  diagnoses, in order, to a procedure line (`PUT /api/notes/{id}/pointers`). A line the coder has
  not linked keeps the default: an add-on (listed in the NCCI add-on table for the date of
  service, with a listed primary on the claim) carries its primary's pointers, every other line
  points to the first four diagnoses.
- Pointer storage: the owner ruled out a migration, and no table holds claim state before
  approval. A choice is a `decisions` row, `suggestion_key` `pointers:<code>:<diagnosis>,...` with
  choice `accept` (an empty list returns the line to the default); the latest row per code applies.
  Decisions are already the append-only record of what a person chose on a note and survive a new
  analysis. Rejected: a billed code-set revision (the billed list is what the provider billed),
  a final code-set revision before approval (remittance matching and audit samples read the latest
  final set whatever the note's status) and the access log. `review_actions.current_claim` puts the
  latest choice on its line and drops a diagnosis that has left the claim; approval writes the
  pointers into the final code set (`pointers`, ICD-10-CM codes, absent for a default line). A
  choice is keyed by the procedure code, so a line whose code changes (a new E/M level) returns to
  the default. Auto-approval writes no pointers and its claims use the default.
- Billing NPI: the provider's own NPI when provider details say `bills_under: individual`,
  otherwise the group NPI from the details, otherwise none. The rendering taxonomy comes from the
  details.
- CSV: one row per line with the claim's diagnoses repeated in `diagnosis_a` to `diagnosis_l`;
  every cell goes through `billing.safe_cell`.
