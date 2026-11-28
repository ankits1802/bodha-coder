# 0051 Blind audits freeze Bodha's suggestion from the claim as uploaded

Date: 2026-11-28

Context: a blind audit or training set freezes, at drawing time, Bodha's suggested claim and the final
claim of each note ([0020](0020-measured-accuracy-and-earned-autonomy.md)). Bodha's side was built from the
latest billed code set with the current suggestions at their default choices. When a coder edits the billed
codes, that edit becomes the latest billed set and the suggestions are re-derived against it, so whatever
the coder typed (a modifier 25, a procedure line, a diagnosis) was carried into "Bodha's" claim and scored
as Bodha agreeing with the auditor. Evaluation runs had the same leak and now read the billed claim as
uploaded ([0049](0049-synthetic-gold-set.md)).

## Choice

- `audit_samples` reads the first billed code set (`code_sets.original_codes(db, note_id, "billed")`),
  rebuilds the suggestions from the current analysis's report against it, and takes that claim at the
  default choices: `findings.suggested_claim(report, billed, icd_release)`, the one function evaluation runs
  now use as well. A note whose current analysis has no report keeps its uploaded billed codes as Bodha's
  side, as before when it had no suggestions.
- The draw needs the ICD-10-CM release for each date of service, so `draw_sample` takes the ICD catalog
  from the request (`POST /api/quality/samples` and `POST /api/training/sets`).
- The final claim is unchanged: the latest final code set.

Rejected: re-reading each sampled note with the model at drawing time, as evaluation runs do. A draw of 40
or 150 notes would wait for the model and spend on it; the report already on the note was produced from the
uploaded claim unless the note was read again after an edit.

## Follows

- Audits and training sets drawn before this change keep their frozen references; only new draws change.
- Remaining exposure: when a note is read again after a billed-code edit (an addendum, a visit type change,
  a retry), that reading gave the model the edited codes as billed. Its report is still used; its claim is
  rebuilt from the uploaded codes, so typed lines and modifiers no longer pass through unless the model
  itself suggests them.
- Training feedback shows Bodha's claim from the same frozen reference, so trainees compare themselves with
  what Bodha suggested on the uploaded claim.
