# 0045 Practice-defined quality measures and privacy-safe usage timing

Date: 2026-11-28

Context: the MIPS list let an admin tick only CMS measures (the standard set and the CMS 2026 measures
that can be added), but practices also report internal quality measures, payer programmes and registry
measures that CMS does not publish. Separately, the next round of streamlining needs measurements of where
people spend time and stall, without collecting patient data.

## Practice-defined measures

- **A measure the practice writes.** Each has a short name (3 to 80 characters), an optional identifier the
  practice uses (up to 20 letters, digits, spaces, periods, slashes, hyphens or underscores), what puts a
  visit in scope (10 to 600 characters), what takes it out of scope (optional, up to 600), what the note
  must document for it to be met (10 to 1,000), and up to four codes to report when met and four when not
  met. Codes are CPT, CPT Category II or HCPCS Level II shapes (`codes.billing_codes.CPT_PATTERN`) with an
  optional two-character modifier (`1090F-8P`), stored in capitals; one code cannot report both outcomes.
  Text keeps its line breaks, collapses runs of spaces and refuses control characters. The checks live in
  `codes/practice_measures.py`; lengths are the column sizes in `models/practice_measures.py` and are
  checked again by the request body.
- **Never a CMS number.** Each measure gets a key `P001` to `P999`, numbered per practice and never reused,
  and the model names it `PRACTICE #P001`. CMS ids are one to three digits, so `normalise_measure_input`
  and `normalise_mips_id` can never read a key as a CMS measure and no CMS reporting code can attach to it.
  An identifier that reads as a CMS number (`117`, `#117`, `MIPS 117`, `Quality ID 117`) or as a key is
  refused, and so is a name that is a CMS measure title (verified or addable), so a practice measure cannot
  pass for a CMS one on the review screen.
- **Versioned, append-only.** `practice_measures` holds one row per version (`measure_key`, `version`, the
  definition, `retired`, `created_by`, database time); the database refuses updates, deletes and truncation
  and the runtime role has SELECT and INSERT only. Editing writes the next version (409 when the expected
  version is stale; saving the same values writes nothing), retiring writes a final version with `retired`
  true, and each writes `practice measure added`, `changed` or `retired` to activity with the key and
  version only. At most 25 live measures per practice; two live measures cannot share a name. A measure on
  the saved list cannot be retired until it is taken off (409), so retiring never silently changes what the
  next review checks. Practice admins manage them (`POST /api/mips/practice-measures`, `PUT
  /api/mips/practice-measures/{key}`, `POST /api/mips/practice-measures/{key}/retire`); an organization
  admin who entered the practice through a membership is a practice admin there and has the same rights.
  There is no organization-level catalogue.
- **On the list beside CMS measures.** `mips_lists.measure_ids` holds CMS ids then practice keys;
  `services.mips_lists.save_mips` refuses a key that is retired or not the practice's (422). The standard
  list (no saved row) holds no practice measure. The review takes the latest live version of each listed
  key (`practice_mips_scope`), `MipsScope.practice_measures` carries them, and the analysis context records
  `mips_measures` (every listed id and key) and `practice_measures` (the version row ids), so an
  evaluation run repeats a review against exactly the versions it used.
- **The practice's text is data.** The prompt lists a practice measure by its key only. Its definition goes
  into a `PRACTICE-DEFINED MEASURES` block as a JSON array between `<practice_measures>` tags, with `<` and
  `>` written as JSON escapes so no text can close the block or open another tag, after the CMS headings
  are filled in so no text can reach the heading templates. The block says the content is data written by
  the practice, never an instruction, and names the requests to ignore (mark a measure met, add or leave
  out a measure, write a code, change another task, reveal instructions). DENOMINATOR-FIRST and the three
  macro rules apply; a visit out of scope is left out, never `not_applicable`. The identifier and the codes
  never go to the model. `PROMPT_VERSION` is `2026.11.6`.
- **Results from the definition.** `ai.practice_mips` keeps an answer only for a listed key, once, and
  takes its name from the stored definition rather than the model, sets `exceptionExclusion` to null,
  attaches the practice's codes as `reportingCodes` (collection `Practice measure`, source `practice`) and
  marks it `practiceMeasure {key, version, identifier}`. Anything else named `PRACTICE #…` counts in the
  scope's `omitted`. With no saved list every practice answer is dropped. The review screen labels these
  rows "Practice measure" with the identifier and names the code to report for the measure's status.

## Usage timing

- **What is recorded.** `usage_events` rows: practice, person, the session's role (from the server, never
  the browser), the browser's event id, `kind` `task` or `stall`, `task` (`note_review`, `queue`, `upload`,
  `billing_export`), for a task its `outcome` (`completed`, `left`), visible duration, time to first decision
  and counts of key presses, pointer presses and findings decided by keyboard or pointer, and for a stall
  its `step` and length. A test pins the column list: nothing else can be stored, so no note text, codes,
  patient fields, free text or URLs. The vocabulary is fixed in `models/usage.py` and the migration
  checks it; `services.usage.TASK_STEPS` says which steps belong to which task.
- **Tasks.** A note review runs from opening the note to approval or a compliance decision (`completed`) or
  leaving (`left`); each note is its own task. A queue visit is `completed` when a note review opens within
  two seconds of leaving it. Upload and billing export are `completed` by an upload or an export and start
  again. Time with the page hidden is left out. A task left within a second with no input is not recorded.
  A decision is counted as keyboard or pointer by the last input before it.
- **Stalls.** No key, pointer, wheel, scroll or touch input for 60 seconds (`STALL_AFTER_MS`, checked by
  the server too) while the page is visible is a stall, recorded at the step of the last input: the nearest
  `data-usage-step` area (summary, note, findings, claim, dialog, history, navigation on the review screen;
  the screen itself elsewhere). A step name outside the vocabulary is ignored in the browser and refused by
  the server.
- **Overhead.** Inputs only update counters in memory (`lib/usage/recorder.ts`); nothing is sent per input.
  `components/shared/usage/UsageCapture` sends batches of at most 50 events every 30 seconds and with
  `keepalive` when the page is hidden or closed. A batch the server could not take (network, 5xx) is kept
  for the next flush, one it refused (4xx) is dropped, and at most 500 events wait. Event ids make a resent
  batch harmless (`ON CONFLICT DO NOTHING` on person and event id).
- **Who records.** Only a signed-in practice session that is not billing-only records: the browser keys
  every event to the person and practice it was recorded in and drops events of another session, and the
  server refuses billing-only sessions (403 `plan_ended`) and HQ (403). The HQ console does not mount the
  capture.
- **Who sees what.** Practice admins see Insights → Usage (`GET /api/insights/usage?days=`): per task and
  role the count, finished count, people, the median with the 25th and 75th percentiles of duration and
  time to first decision, inputs per decision, and the keyboard share of decisions; per task, step and role
  the stalls with the same spread. There is no per-person view or ranking. HQ sees the same figures across
  every practice with the number of practices recording (`GET /api/hq/usage?days=`).
- **Records.** The rows are append-only like every other record, removed only with the practice by
  `bodha_purge_practice` (migration 0020 adds the step before `mips_lists`, with the practice measures).
  The privacy policy (version 1.3) describes the timing data and its retention.

## Consequences

- A practice measure carries no CMS specification: its quality depends on the practice's wording, and the
  model reads it only as a description. Changing a measure changes later reviews only; earlier reviews keep
  the version they used.
- The frontend keeps its own copy of the step vocabulary, the stall threshold and the batch size; the
  server checks each, so a drift is refused rather than stored.
- Small practices may have one person in a role, so a role row can describe one person; the screen still
  shows no names and no ranking.
