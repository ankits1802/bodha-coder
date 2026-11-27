# AI governance

A practice's compliance committee can adopt this page as the description of how Bodha Coder uses
artificial intelligence. It states what the product does today; the practice fills in the owners and
the review dates.

## Purpose and limits

Bodha Coder uses a large language model to read a visit note and propose a review: the evaluation and
management level with its decision-making or time basis, diagnoses with their status, a verdict on
each billed code, modifiers and add-on codes, documentation gaps with compliant provider questions, an
audit checklist, quality measures and, when switched on, risk-adjustment conditions.

The model proposes; people decide. No claim leaves Bodha without a person approving it, and nothing is
submitted to a payer by Bodha.

## Controls around the model

| Control | How it works |
|---|---|
| Code validity | Every suggested ICD-10-CM code is checked against the CDC release for the date of service; every procedure code against the CMS physician fee schedule list or the E/M families. A code that fails becomes a review item, never a suggestion. |
| Risk adjustment | HCC categories, hierarchies and scores are computed from the CMS-HCC V28 software files, not by the model. |
| Evidence | Every suggestion carries verbatim quotes from the note; the screen shows whether each quote is found in the note. |
| Provider questions | Questions follow the AHIMA/ACDIS query practice: multiple choice with clinically reasonable options, an "other" option, no mention of payment or risk scores. The provider's own answers become the signed addendum. |
| Routing | E/M billed two or more levels above the documentation, critical audit risks and flagged notes go to compliance; the person who flagged a note cannot clear it. |
| Human approval | Approval needs a person with an approving role; held claims cannot be approved until the provider answers. |
| Record | Every model run (inputs, model, prompt version, tokens, raw reply in storage), every suggestion with its reasoning and evidence, every decision, code-set revision and note-text revision is kept. Access to patient information is logged. |
| Failure | A read that fails is marked with its reason and retried; it never produces a partial claim. |

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
roles the practice chooses, and the access log is kept for at least six years.

## Owners and reviews

| Role | Person | Review |
|---|---|---|
| Executive owner |  |  |
| Compliance owner |  |  |
| Coding lead who validates output |  |  |
| Security owner |  |  |

Review this page at least once a year and whenever the model, the prompt version or the routing rules
change.
