# 0020 Measured accuracy and earned autonomy

Context: buyers do not believe vendor accuracy claims. Bodha has to show its accuracy on each
practice's own notes with a method a compliance committee can repeat, and may approve claims on its
own only where that measurement supports it.

## Sampling

- A blind audit draws approved or exported notes whose date of service falls in a chosen period, for
  the practice, one provider or one specialty. The default is 30 notes, enough for a first look; a
  specialty audit defaults to 150, the size AAPC-style audits use per specialty. Fewer notes are drawn
  when fewer exist; none is refused.
- Candidates are sorted by id and shuffled with `random.Random(seed)`; the 63-bit seed comes from
  `secrets` and is stored with the sample, so the draw can be repeated and checked.
- Notes go round-robin to the chosen reviewers, never to the person who approved the note. A note
  only its approver could review is skipped.
- No table was added: each sampled note is one `audit_samples` row, and `result.sample` carries the
  sample id, scope, period, size, seed and requester. Samples are found by that id.

## Blinding

- At drawing time Bodha's suggestion (the billed codes with every suggestion at its default choice,
  from the current analysis) and the final claim are frozen in `result.reference`, so later changes to
  the note do not move the comparison.
- The reviewer's endpoints return the note texts and a signed PDF link and nothing else. Results show a
  note's references only after it is coded, so an admin who is also a reviewer is not unblinded.
- Blinding is enforced on these screens. A reviewer who can read notes could still open the note in
  the queue; choose reviewers who did not work the notes.

## Metrics

| Element | Measure |
|---|---|
| E/M | exact code match; when it differs, the direction from `compare_em`: higher, lower, another family, or one side has no E/M code |
| ICD-10-CM | precision (matched over Bodha's or the claim's codes) and recall (matched over the reviewer's), pooled over all codes, their F1, and the share of notes with the exact set |
| Modifiers | exact match of the set of modifiers on the claim's CPT codes |

The reviewer is the reference. Each element is compared with Bodha's suggestion and with the final
claim, overall and per provider.

## Intervals

Every rate carries a Wilson score 95% interval (z = 1.959964). It stays inside 0 to 1, behaves at 0%
and 100% and at small n, where the normal approximation fails. ICD-10 precision and recall count codes,
and codes within one note are not independent, so their intervals are narrower than a note-level
interval; the per-note exact-set rate is reported beside them for that reason.

## Evaluation set and drift

- An admin adds approved notes; the expected answer is the final claim with its E/M code and MDM level.
- A run uses the current `GEMINI_MODEL` and `PROMPT_VERSION`, rebuilds the inputs from the case's
  analysis context (the same sections, billed codes and MIPS scope) and current note texts, and writes
  nothing to the note. Each case is read twice: the first read is scored against the expected claim,
  the two reads against each other (run-to-run consistency). Raw replies are stored like analyses.
- A run is marked dropped when E/M exact agreement, ICD-10 F1 or modifier agreement falls more than
  five points below the previous finished run: larger than the change one or two cases make in a set
  of a few dozen, small enough to catch a prompt or model change that matters.
- The level-mix check compares the MDM level of Bodha's suggested E/M code for notes with a date of
  service in the last 30 days with the 90 days before, by a chi-square test of homogeneity with
  adjacent sparse levels pooled until every expected count is at least five. Below p 0.05 it is
  shifted; with fewer than 30 notes in either window there is no verdict. A shift can come from the
  case mix as much as from the model, so it asks for a look, not a stop.

## Earned autonomy

- A provider becomes eligible only from their notes in the latest completed blind audit that contains
  them: at least 30 notes, the Wilson lower bound of E/M exact agreement at least 90%, and Bodha higher
  than the auditor on at most 5% of them. The lower bound, not the point estimate, makes the evidence
  carry its own uncertainty. Over-coding is the costly error for a practice, so it has its own limit.
- The rule is strict by design: 30 of 30 gives a lower bound of 88.6% and does not qualify; 35 of 35
  (90.1%), 40 of 40 or 143 of 150 do. A practice that wants autonomy should audit at least 35 of a
  provider's notes, or use a specialty-sized sample.
- The check runs again for every note, so a newer audit below the threshold stops auto-approval at
  once. Only notes Bodha placed in the approve lane as matching, never flagged or through compliance,
  without review items, critical audit risks, open questions or a sent request, qualify.
- One in ten qualifying notes is held for a person, chosen by the first eight hex digits of the
  SHA-256 of the note id modulo 10: deterministic, so it cannot be gamed by re-reading, and spread
  evenly. Their human decisions are the ongoing check on autonomy.
- An auto-approval writes the final code set with reason `auto` and no actor, and an `approved` access
  entry by `Bodha (auto)`. `review_actions.approve` is not reused because it writes the actor's user id
  into foreign keys; there is no system user.

Follows: the worker must run `evaluation_runs.run_next_evaluation`, and placement or the analysis
pipeline must call `auto_approval`; `code_sets.py` holds the two code-set queries that `analysis.py`
should import instead of its own copies.
