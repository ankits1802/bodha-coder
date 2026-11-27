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
| Code validity | Every suggested ICD-10-CM code is checked against the CDC release for the date of service; every procedure code against the CMS physician fee schedule list or the E/M families. A code that fails becomes a review item, never a suggestion. |
| Risk adjustment | HCC categories, hierarchies and scores are computed from the CMS-HCC V28 software files, not by the model. |
| Evidence | Every suggestion carries verbatim quotes from the note; the screen shows whether each quote is found in the note. |
| Provider questions | Questions follow the AHIMA/ACDIS query practice: multiple choice with clinically reasonable options, an "other" option, no mention of payment or risk scores. The provider's own answers become the signed addendum. |
| Routing | E/M billed two or more levels above the documentation, critical audit risks and flagged notes go to compliance; the person who flagged a note cannot clear it. |
| Human approval | Approval needs a person with an approving role, except notes auto-approved under earned autonomy, which are recorded as Bodha (auto); held claims cannot be approved until the provider answers. |
| Record | Every model run (inputs, model, prompt version, tokens, raw reply in storage), every suggestion with its reasoning and evidence, every decision, code-set revision and note-text revision is kept. Access to patient information is logged. |
| Failure | A read that fails is marked with its reason and retried; it never produces a partial claim. |
| Measured accuracy | Admins or compliance draw random samples of approved notes (40 by default, 150 for a specialty) and assign them to reviewers who did not approve them. Reviewers code each note blind, seeing only its text and PDF. Agreement with Bodha's suggestion and with the final claim is reported per element (E/M exact and its direction, ICD-10 precision, recall and exact set, modifiers) with Wilson 95% intervals, per provider and per note. |
| Validation and drift | Approved notes chosen by an admin form an evaluation set. Each evaluation run reads every case twice with the current model and prompt without changing the note, records agreement with the approved claim and between the two reads, and keeps the raw replies. A run whose E/M, ICD-10 F1 or modifier agreement is more than five points below the previous run is marked dropped. The mix of suggested E/M levels in the last 30 days is compared with the 90 days before (chi-square, p below 0.05 marked shifted). |
| Earned autonomy | Auto-approval is off for every provider. An admin can switch it on only when the provider's latest completed blind audit has at least 30 of their notes, the Wilson 95% lower bound of E/M exact agreement is at least 90% (which takes at least 35 agreeing notes, hence the 40-note default audit) and Bodha coded higher than the auditor on at most 5%; the check is repeated for every note. Only notes Bodha found to match, with no questions, flags, compliance history or review items, are approved as Bodha (auto) with reason auto in the record, and one in ten of them is held for a person. |

## Model and change control

| Item | Value |
|---|---|
| Model | Google Gemini, `GEMINI_MODEL` (default `gemini-3.8-flash`) |
| Platform for patient data | Vertex AI under the customer's Google Cloud business associate agreement (`GEMINI_BACKEND=vertex`); the Gemini Developer API is for synthetic data only |
| Prompt version | `PROMPT_VERSION` in `backend/app/ai/review.py`, stored on every analysis |
| Change process | Prompt and model changes are code changes reviewed through pull requests, recorded in `docs/decisions/`, tested on GitHub Actions, and visible per note in the analysis history |

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
