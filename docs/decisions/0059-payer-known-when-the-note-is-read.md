# 0059 The payer is known when the note is read

Date: 2026-11-28

Context: the payer was chosen after the model had read the note (`PUT /api/notes/{id}/payer`), so the read
was payer-neutral. Medicare guidance (G2212 instead of 99417, telehealth places and modifiers, G2211, audio-only,
Medicare Advantage) reached a claim only through the claim check afterwards
([0054](0054-prolonged-service-99417.md), "the payer is not known when the note is read"). The payer is now
recommended at upload, suggested from page one, used as the provider's usual payer, and passed into the read.
It is never required.

## Where a note's payer comes from

| Path | Payer, in order |
|---|---|
| Upload screen and drop flow | the file's own choice (`details[].payer`), else the batch choice (form field `payer`), else the provider's usual payer |
| Watched folder, email intake | the payer page one names at or above the threshold, else the provider's usual payer, else none |
| API, a file's `payer` key | present (even `null`): that choice, `null` meaning none; absent: the batch choice, then the usual payer. A batch `payer` sent empty means none for every file without its own key |

- The screen fills each row visibly, the way the usual place is filled: a confident page-one payer, else the
  provider's usual payer, and it sends every file's payer key. So "None" chosen by the person stays none on the
  server; only a client that leaves the key out gets the usual payer. Read in `services.uploads` as
  `UploadFile.payer`: `None` is "not chosen", `NO_PAYER` (`""`) is "chosen: none".
- A chosen payer must be an active payer of the practice ("{file}: choose an active payer", 422). The usual
  payer is `providers.payer` (migration 0026), set in the provider dialog from the active payers; removing or
  turning off a payer clears it as a usual payer, and a usual payer that is not active is ignored.
- The document wins over the usual payer on the intake paths, as a page-one place wins over the intake place:
  the face sheet describes this patient, the usual payer only the provider's typical patient.
- The payer stays on `notes.payer`. Its first value is not a change, so no `note_changes` row is written at
  upload; later changes are recorded as before.

## Page one

`services/payer_matching.payer_in(text, payers)` matches against the practice's active payers only:

| Evidence | Confidence |
|---|---|
| a listed payer's name within eight words after an insurance label (insurance, insurer, payer, payor, coverage, carrier, health plan, plan name); the longest name wins, two names of the same length name nobody | 0.9 |
| a Medicare beneficiary identifier (CMS MBI format: 11 characters, letters S, L, O, I, B and Z never used) within 32 characters after mbi, medicare, beneficiary or member, or a labelled Medicaid member id, when the practice lists exactly one payer of that plan type | 0.85 |
| plan words after an insurance label (medicare advantage, medicare, medicaid) and exactly one listed payer of that plan type | 0.7 |
| a listed payer's name anywhere else on page one | 0.6 |

The rule is the provider and date rule (`CHECK_BELOW`, 0.8): at or above it the payer is applied (preview
`payer_confident`, intake), below it only suggested (the screen puts it in a Suggested group of the row's
list). The plan-words rung stays below the threshold because "Aetna Medicare" is an Advantage plan that the
word medicare alone would send to traditional Medicare. The match returns only a payer id and a confidence:
the member id is never returned, stored or logged.

## The read

- `ReviewInputs.payer` is `payer_rules.Payer` (plan type and family, the Cigna family read from the name as the
  payer rules do), from `payers.review_payer`. The encounter context carries `payer` as
  `{planType, family}` (`other` for a plan type outside the rules), or `null`; the analysis context records
  `payer` as `{plan_type, family}`. The payer's name is not sent: only the two values the rules use.
- `PROMPT_VERSION` 2026.11.8. The context block says what `payer` is and that it is null when unknown. A new
  E/M step 6 holds the payer rules: Medicare G2212 never 99417, telehealth by place 02 or 10 and 95 only with
  02, 10, 19 or 22, audio-only at home, G2211 through 2026 (with the CR 13705 modifier 25 exception, never
  from 2027); Medicare Advantage G2212 with the plan's own policy named, audio-only diagnoses outside risk
  adjustment from 2026; commercial, Medicaid and other 99417 and no Medicare codes; Cigna's level 4 and 5
  policy. With `payer` null the step says to apply the steps as written, which is the earlier wording, so an
  unknown payer reads as before.
- G2211 was never in the prompt before; for Medicare it now is. The add-on path already accepts it.

## Read again with this payer

`payers.payer_changed(practice, note, analysis)` compares the guidance the read used (its context's `payer`)
with the note's payer now. Guidance groups are Medicare, Medicare Advantage and the rest, each with its family,
plus unknown, so commercial to Medicaid changes nothing and Aetna to Cigna or unknown to Medicare does. The note
view's `analysis.payer_changed` drives a Read again with this payer button beside the payer select for a
ready note and the roles that may retry. It reuses `POST /api/notes/{id}/retry`, which now also takes a ready
note whose payer changed (analysis reason `payer`, access entry `read again with payer`) and answers 409
"the payer has not changed since this note was read" otherwise. Nothing re-reads on its own: a coder's
decisions belong to the read they were made on, and a payer fix on a note already worked should not drop them
silently. Notes read before this change have no payer in their context, so a note that has a payer offers
Read again once.

## Evaluation

An evaluation re-read takes the payer the note had when it was approved: the value of `payer` at
`notes.approved_at` from `note_changes` (the last change before it, else the first change's old value, else the
note's payer), read through the practice's payer list. A payer changed after approval does not move the
evaluation. The gold set loader lists one payer per plan type under the name the PDFs print on their
Coverage line (Medicare Part B, Medicaid, Commercial PPO, reused when listed), uploads each case with its
payer, and sets it before approval on a note uploaded earlier without one.

## Not done

- No `payer` in `approved_claims.content`: the payer at approval comes from the change history instead, so
  the snapshot schema stays at version 1.
- Evaluation results do not show the payer each case was read with.
