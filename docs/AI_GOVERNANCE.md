# AI governance

A practice's compliance committee can adopt this page as the description of how Bodha Assure uses
artificial intelligence. It states what the product does today; the practice fills in the owners and
the review dates.

## Purpose and limits

Bodha Assure uses a large language model to read a visit note and propose a review: the evaluation and
management level with its decision-making or time basis, diagnoses with their status, a verdict on
each billed code, modifiers and add-on codes, documentation gaps with compliant provider questions, an
audit checklist, quality measures and, when switched on, risk-adjustment conditions.

The model proposes; people decide. A claim leaves Bodha only after a person approves it, unless an admin
has switched on earned autonomy for that provider after a passing blind audit (see below); even then one
in ten notes is held for a person. Nothing is submitted to a payer by Bodha.

## Controls around the model

| Control | How it works |
|---|---|
| Code validity | Every suggested ICD-10-CM code is checked against the CDC release for the date of service; every procedure code against the CMS physician fee schedule list, the E/M families or the commercial codes Bodha adds to them (99417). A code that fails becomes a review item, never a suggestion. Prolonged time (99417, Medicare's G2212) is suggested only with 99205 or 99215 chosen by documented total time and with the units that time gives, checked by code rather than left to the model; a billed one the review does not support is proposed for removal or unit correction. |
| Payer | The note's payer is recommended, never required. A person can choose it for a batch or a file at upload, an admin can give each provider a usual payer, and page one can name it (insurance or plan name, a Medicare or Medicaid member id); the page-one payer is applied only at 0.8 confidence or more, like provider and date, and only suggested below that. Bodha adds to the encounter context only the payer's plan type (Medicare, Medicare Advantage, Medicaid, commercial or other) and, for Cigna, its family; it adds neither the payer's name nor a member id (the note itself is read as before). With a payer the prompt applies payer rules (Medicare G2212 rather than 99417, telehealth places and modifiers, G2211 through 2026, Medicare Advantage prolonged time and audio-only; 99417 and no Medicare codes for the rest); without one it says the payer is unknown and the steps apply as before. A payer changed after the read never re-reads the note by itself: Read again with this payer is offered when the change alters that guidance. The claim check still flags the payer's rules on the claim ([0059](decisions/0059-payer-known-when-the-note-is-read.md)). |
| Practice measures | A quality measure a practice defines for itself is sent to the model by its key (`PRACTICE #P001`, never a CMS number) with its wording quoted as data in its own block, which the prompt says is never an instruction; the model writes no codes, and the result takes its name and reporting codes from the stored definition. Each edit is a new version and every run records the versions it used. |
| Risk adjustment | HCC categories, hierarchies and scores are computed from the CMS-HCC V28 software files, not by the model. |
| Evidence | Every suggestion carries verbatim quotes from the note; the screen shows whether each quote is found in the note. |
| Provider questions | Questions follow the AHIMA/ACDIS query practice: multiple choice with clinically reasonable options, an "other" option, no mention of payment or risk scores. The provider's own answers become the signed addendum. |
| Routing | E/M billed two or more levels above the documentation, critical audit risks and flagged notes go to compliance; the person who flagged a note cannot clear it. |
| Human approval | Approval needs a person with an approving role, except notes auto-approved under earned autonomy, which are recorded as Bodha (auto); held claims cannot be approved until the provider answers. |
| Departing from Bodha | A person who turns down a proposed change, keeps a billed code Bodha flagged, or edits the billed codes or diagnosis links by hand chooses a reason (documentation supports the billed code, payer policy, provider's answer, coding guideline, clinical context, or other with a note). A note cannot be approved while such a choice has no reason. Practices cannot turn this off. |
| Level confirmation | When the practice turns it on, an approved visit level that differs from the billed one is sent to the provider, who sees both levels and the evidence and confirms or disagrees with a comment. A disagreement reopens the note; with hold on, the claim cannot be exported until the provider confirms. |
| Record | Every model run (inputs, model, prompt version, tokens, raw reply in storage), every suggestion with its reasoning and evidence, every decision with its reason, code-set revision and note-text revision is kept. Each approval freezes the claim with its decisions, approver, model, prompt version and document checksum; exports use that frozen claim and keep the exact file with its checksum. Provider statements keep the wording they accepted and the text they were shown; review comments are kept even when removed from view. Access to patient information is logged, and a per-note audit package with a checksum manifest can be handed to an auditor. |
| Failure | A read that fails is marked with its reason and retried; it never produces a partial claim. |
| Signature check | A drawn or photographed signature is sent to Gemini alone (no note, no patient details) with a fixed prompt (`SIGNATURE_CHECK_VERSION` in `backend/app/ai/signature_check.py`) that treats the image as data and answers only whether it is one handwritten signature, whether other text or several signatures appear, and named image issues. A signature that fails is refused and not kept; when the check cannot run the person can type their name instead. The verdict, model and check version are stored with the signature. The model never decides whether a record is valid: seals are checked with cryptography. |
| Measured accuracy | Admins or compliance draw random samples of approved notes (40 by default, 150 for a specialty) and assign them to reviewers who did not approve them. Reviewers code each note blind, seeing only its text and PDF. Agreement with Bodha's suggestion and with the final claim is reported per element (E/M exact and its direction, ICD-10 precision, recall and exact set, modifiers) with Wilson 95% intervals, per provider and per note. Bodha's suggestion is rebuilt from the claim as it was uploaded, so a coder's edit of the billed codes is never credited to Bodha. |
| Validation and drift | Approved notes chosen by an admin form an evaluation set. Each evaluation run reads every case twice with the current model and prompt, from the claim as it was billed, with the payer the note had when it was approved and without changing the note, records agreement with the approved claim and between the two reads, and keeps the raw replies. Besides the visit code, diagnoses and modifiers it scores procedure lines, add-on codes (G2211, G2212, 99417), units and place of service, each on the cases it applies to and with its case count. A run whose E/M, ICD-10 F1 or modifier agreement is more than five points below the previous run is marked dropped. The mix of suggested E/M levels in the last 30 days is compared with the 90 days before (chi-square, p below 0.05 marked shifted). |
| Earned autonomy | Auto-approval is off for every provider. An admin can switch it on only when the provider's latest completed blind audit has at least 30 of their notes, the Wilson 95% lower bound of E/M exact agreement is at least 90% (which takes at least 35 agreeing notes, hence the 40-note default audit) and Bodha coded higher than the auditor on at most 5%; the check is repeated for every note. Only notes Bodha found to match, with no questions, flags, compliance history or review items, are approved as Bodha (auto) with reason auto in the record, and one in ten of them is held for a person. |

## Model and change control

| Item | Value |
|---|---|
| Model | Google Gemini, `GEMINI_MODEL` (default `gemini-3.8-flash`) |
| Platform for patient data | Vertex AI under the customer's Google Cloud business associate agreement (`GEMINI_BACKEND=vertex`); the Gemini Developer API is for synthetic data only |
| Prompt version | `PROMPT_VERSION` in `backend/app/ai/review.py`, stored on every analysis; 2026.11.8 added the payer to the encounter context and the payer rules ([0059](decisions/0059-payer-known-when-the-note-is-read.md)) |
| Change process | Prompt and model changes are code changes reviewed through pull requests, recorded in `docs/decisions/`, tested on GitHub Actions, and visible per note in the analysis history |

## Synthetic gold set

Bodha keeps a fixed set of 48 synthetic visit notes for measuring accuracy release over release
(`tools/gold_set/`, [0049](decisions/0049-synthetic-gold-set.md)). The notes are fictional (Synthetic
Patient 01 to 48, invented practice, facility and providers) and cover office new and established
visits, initial and subsequent nursing facility visits, audio-video and audio-only telehealth, visits
set by decision-making and by time, G2211, prolonged time, modifier 25 with minor procedures, and
diagnosis specificity, combination codes, laterality and 7th characters. Each was uploaded with a claim
as a practice might bill it: 21 correct, 16 one level too high, 8 one level too low, 2 two levels too
high and 1 with a visit that is not separately billable.

| Item | How it works |
|---|---|
| Expected answers | Written by construction under the 2021 and later AMA E/M guidelines and the 2023 nursing facility rules, with a rationale for every code and modifier. A validator checks each against the ICD-10-CM release for the date of service, Bodha's code list, the NCCI edits and Bodha's Medicare rules, and rebuilds each visit level from the documented decision-making elements and time. |
| Loading | A script lists one payer per plan type in a dedicated evaluation practice under the name each PDF prints as its coverage, uploads each note through the public API with its payer, waits for Bodha's review, records the expected claim as the coder's decision with the override reason "coding guideline", approves it and marks it as an evaluation case. It can be re-run safely. |
| Measuring | A normal evaluation run reads every case twice with the current model and prompt; a report script writes the agreement by element with 95% intervals, by group, and lists every disagreement. |
| Limits | Procedure lines, add-on codes, units and place of service are scored only on the cases they apply to (few in this set, so their intervals are wide), and Bodha never changes the place of service. Run-to-run consistency covers the visit code, diagnoses and modifiers only. Notes whose right outcome is a provider query are not in the set, because a run cannot score a query. Bodha's suggested claim cannot remove a visit code or a modifier, so one case can only disagree; results are shown with and without it. 48 notes give wide intervals: one case moves a rate by about two points. |
| Status | **Provisional.** No certified coder has checked the expected answers yet. Numbers from this set are provisional until one does and the review is recorded. |

### First run, 2026-11-28 (provisional)

Run b473489a in production, gemini-3.8-flash, prompt 2026.11.8: 48 cases, 46 scored. Two reads (GS-26 and GS-41) timed out at the model after retries and did not score.

| Element | Agreement | 95% interval | Cases |
|---|---|---|---|
| Visit code exact | 100% | 92.3% to 100% | 46 / 46 |
| Visit code higher or lower than expected | 0% each | 0% to 7.7% | 0 / 46 |
| ICD-10-CM precision | 100% | 100% to 100% | 76 / 76 codes |
| ICD-10-CM recall | 97.4% | 93.8% to 100% | 76 / 78 codes |
| ICD-10-CM exact set | 95.7% | 85.5% to 98.8% | 44 / 46 |
| Modifiers exact | 100% | 92.3% to 100% | 46 / 46 |
| Procedure lines, add-ons, units | 100% | wide (3, 12 and 15 cases) | all |
| Two reads agree on every element | 95.7% | 85.5% to 98.8% | 44 / 46 |

The two diagnosis misses were codes the expected answer adds beyond what was billed: Z79.84 (long-term oral
hypoglycemics, GS-11) and E78.5 (hyperlipidemia, GS-17). These notes were written to meet each level
unambiguously, so the run measures the reading on clean documentation; real notes are less tidy, and the
figures should not be quoted publicly until a certified coder has checked the expected answers and a
sample of real, de-identified notes has been measured the same way.

## Data handling

Patient information is sent to the model only to review the note it came from. Documents are stored
encrypted in the practice's object storage under keys without names. Messages to providers and staff
contain no patient details. Access tokens are short lived, two-step verification is required for the
roles the practice chooses, and the access log is kept for seven to ten years, never under 2557 days.
Each run keeps the rendered prompt, its SHA-256, the code version, the generation settings and the
document sent, and every failed attempt keeps its error
([0038](decisions/0038-seven-year-retention-and-tamper-evidence.md)).

## Owners and reviews

| Role | Person | Review |
|---|---|---|
| Executive owner |  |  |
| Compliance owner |  |  |
| Coding lead who validates output |  |  |
| Security owner |  |  |

Review this page at least once a year and whenever the model, the prompt version or the routing rules
change.
