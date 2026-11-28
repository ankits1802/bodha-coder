# 0038 Seven-year retention and tamper evidence

Date: 2026-11-28

Context: the owner requires every record to be kept at least seven years (2557 days) and to stand up
to payer, OIG, RAC and HIPAA audits. An audit review found hard deletes of notes and practices, an
access log kept six years, timestamps written by the application, no database guard against edits,
AI runs that could not be reproduced, overwritten field values and an access log auditors could not
search. Migration 0015 and the services below close those gaps. It supersedes the deletion and
access-log parts of [0011](0011-practice-deletion-and-retention.md).

## No hard deletes

- **Void, not delete.** `POST /api/notes/void` (`services.note_voids`) sets the note's status to
  `voided`, keeps the earlier status in `notes.status_before_void` and records `voided_at`,
  `voided_by` and the required `void_reason` (3 to 2000 characters). Every row and file stays. A coder
  may void only a note Bodha never read (status `queued` or `failed` and no current analysis); an admin
  any note except one being read; a note with an open provider request is refused. Queued analyses of
  the note become `superseded`. `POST /api/notes/{id}/restore` (admins, reason required) puts the
  earlier status back (a note that was queued is queued for a new read). A status was chosen over a
  separate flag so every list that filters by status hides voided notes without a second predicate;
  lists that do not filter by status (insights, E/M mix, level mix, query metrics, claim and day checks,
  remittance matching, batch counts) exclude `voided` explicitly. Search still finds a voided note,
  shown as voided, so an admin can reach it to restore it.
- **The same PDF can come back.** `uq_notes_practice_file` is a unique index on
  `(practice_id, file_sha256)` for notes that are not voided, so a PDF voided by mistake can be uploaded
  again; restoring is then refused while another note holds it.
- **Close, not delete.** `POST /api/hq/practices/{id}/close` (HQ, practice ended or blocked, no live
  subscription, typed name) sets status `closed` and `closed_at`, signs every user out, cancels open
  provider requests and supersedes queued analyses. All data stays. `closed_at` is stamped by the
  database and can never change again (trigger `bodha_closure`), and a check ties the `closed` and
  `purged` statuses to it, so closing is final for the runtime.
- **Purge only after the retention period.** `POST /api/hq/practices/{id}/purge` (HQ, typed name) is
  refused until `RETENTION_DAYS` (default and minimum 2557) after `closed_at`, measured by the
  database clock. It first writes the practice's whole access log, with its chain columns, to
  `archives/practices/{id}/access-log.csv` and records its SHA-256 and entry count in HQ activity, then
  calls `bodha_purge_practice`, which deletes the practice's rows in foreign-key order and marks the
  practice row `purged` (the row stays as a tombstone). HQ activity is never deleted. The objects under
  `practices/{id}/` are removed afterwards; the orphan sweep finishes what a failed removal leaves.
- **Files belong to their records.** The orphan sweep holds every object under a note's folder while
  the note row exists, every evaluation reply while its run exists and every remittance file while its
  row exists, and it never empties the folder of a practice that has no row. Intake moves a file out of
  the inbox only after reading the kept copy back and comparing its SHA-256, and deletes only keys that
  are new arrivals inside the inbox. The email intake function stores the raw message under
  `ses-retained/<recipient>/<message id>` before it does anything else.
- **Credentials are not records.** Recovery codes, sign-in links and invites, sessions, rate-limit
  events and sign-in identities may still be deleted; the MIPS measure list and the evaluation set are
  practice configuration whose changes HQ activity records, and stay deletable too.

## Retention minimums

- `practices.access_log_years` is 7 to 10 (default 7); migration 0015 raises every value below 7 and
  the check constraint is `>= 7`.
- The daily access-log purge asks `bodha_purge_access_log(practice, cutoff)` for each practice, with the
  cutoff the earlier of the practice-calendar day `access_log_years` back and the database time minus
  `RETENTION_DAYS`. The function refuses any cutoff later than 2557 days before its own clock, removes
  only a prefix of the practice's chain and writes an `audit_chain_anchors` row (last removed sequence
  and hash, rows removed) so the rest still verifies.

## Tamper evidence in the database

- **Database time.** Append-only tables take `created_at` (`billing_events.received_at`) from
  `clock_timestamp()`: a server default, and trigger `bodha_stamp` overwrites any value the application
  sends. The models use `LedgerMixin`, which sends none and reads the stamped value back with
  `RETURNING`. `clock_timestamp()` rather than `now()` keeps rows written in one transaction in order.
- **Append-only tables** (trigger `bodha_append_only` refuses UPDATE and DELETE): `decisions`,
  `code_sets`, `suggestions`, `note_texts`, `access_log`, `activity`, `billing_events`,
  `remittance_lines`, `batches`, `analysis_failures`, `note_changes`, `audit_chain_anchors`.
- **Written-once columns** (trigger `bodha_write_once`: a column may go from NULL to a value once):
  `analyses` (`id`, `note_id`, `revision`, `reason`, `created_at`, `report`, `response_key`,
  `prompt_key`, `prompt_sha256`, `document_key`, `app_version`, `generation`, `model`, `prompt_version`,
  `input_tokens`, `output_tokens`, `finished_at`), every column of `remittances`, and the request and
  signed answer of `addendum_requests` (`id`, `created_at`, `practice_id`, `note_id`, `analysis_id`,
  `provider_id`, `questions`, `sent_by`, `answers`, `addendum_text`, `answered_at`). Status, attempts,
  timing, context and error stay writable while a run is in progress.
- **No delete of retained rows** (trigger `bodha_no_delete`): the written-once tables and `notes`,
  `practices`, `users`, `providers`, `subscriptions`, `audit_runs`, `audit_samples`, `eval_runs`.
  TRUNCATE of every retained table is refused (`bodha_no_truncate`).
- **Who may bypass.** Each trigger lets a change through only when the transaction set
  `bodha.maintenance = 'on'` *and* the current role is a member of the table's owner (the migration
  user). The runtime role can set the setting but is not the owner, so it never bypasses. The purge
  functions are `SECURITY DEFINER` (owned by the migration user, `search_path` pinned), set the setting
  locally and restore it. Migrations alter schema as before; a migration that must change data in these
  tables sets the setting first. Tests run as the owner and use the same setting to build old rows.
- **Hash chains.** `access_log` (one chain per practice) and `activity` (one chain) carry `chain_seq`,
  `prev_hash` and `row_hash = sha256(prev_hash || content)`, computed by trigger `bodha_chain` under an
  advisory lock per chain, where the content is a fixed `jsonb` array of the row's columns with the
  time as UTC text (`bodha_access_log_content`, `bodha_activity_content`). A fixed column list was
  chosen over hashing the whole row so a column added later does not break old links; changing the
  content means a new version of these functions. The first link starts from 64 zeros or the latest
  anchor. `bodha_verify_chain(chain)` walks a chain and reports the first missing sequence ("missing
  rows"), wrong `prev_hash` ("broken link") or wrong `row_hash` ("changed row");
  `bodha_verify_audit_log()` checks every chain. HQ runs it from `POST /api/hq/audit-log/verify`, which
  records `audit log verified` in the activity chain with the result, so each check also leaves a
  dated checkpoint. Existing rows were chained by migration 0015 in `(created_at, id)` order. The lock
  serialises writes per practice; a transaction that writes the access log then waits on a row lock
  held by one waiting for that practice's chain is a deadlock Postgres breaks by failing one request.
- **Least privilege.** Migration 0015 creates `bodha_runtime` when `RUNTIME_DATABASE_PASSWORD` is set
  (from a SCRAM-SHA-256 verifier computed in Python, so the password never appears in SQL text) and, in
  any database where the role exists, grants CONNECT, schema USAGE, SELECT and INSERT on every table,
  UPDATE on every table that is not append-only, DELETE only on the credential and configuration tables
  above, EXECUTE on the two purge functions (revoked from PUBLIC) and default SELECT and INSERT on tables
  later migrations create. No TRUNCATE, no schema rights, nothing on `alembic_version`. Without the
  variable no role is created, so Docker Compose and CI keep one user. `DATABASE_URL` is the runtime
  connection; `MIGRATION_DATABASE_URL` (falling back to `DATABASE_URL`) is what Alembic uses. A table a
  later migration adds gets SELECT and INSERT only; that migration grants anything more.

## Reproducible AI runs

- `ReviewOutcome.requests` carries each request exactly as sent (system instruction, rendered prompt,
  response schema), paired with its reply; `ModelReply` carries the temperature and whether the schema
  was applied (Gemini retries once without it).
- `services.analysis_records.keep_run_inputs`, called from `run_analysis` after the outcome is stored,
  writes `{version, prompt_version, document {key, sha256}, requests [...]}` to
  `practices/{p}/notes/{n}/analyses/{revision}.prompt.json` beside the raw reply and stores on the row
  `prompt_key`, `prompt_sha256` (of the stored bytes), `app_version` (`APP_VERSION`, the image tag),
  `generation` (per call: model, schema SHA-256 of the canonical JSON, temperature, schema applied) and
  `document_key`. The analysis context keeps the billed codes with modifiers and units.
- `fail_attempt` writes one `analysis_failures` row per failed attempt (attempt number, error, whether
  it will be retried); `analyses.error` still shows the latest.
- These are separate helpers so `services/analysis.py` changes by four lines.

## Before and after

`note_changes` keeps each in-place change of a note with old and new values, who and when: `status`
(void and restore, with the reason), `flag` (set, and cleared by a compliance return with its reason),
`payer`, `assignee` and `visit_type`. The note history shows them, payers and people by name. HQ
practice updates and renewals write `activity.changes`, a list of `{field, before, after}` for name,
time zone, status, plan, seats and renewal date, shown in HQ activity.

## Access log for auditors

`GET /api/access-log` (admins and compliance) filters by practice-calendar date range, person,
action, note, and patient name or birth date (through the notes' patient fields; the log rows hold no
patient data), and returns the actions seen in the range. `POST /api/access-log/export` returns the
same rows as CSV with the chain columns, up to 100,000 rows (more is refused with the count). Each view
and export writes `viewed access log` or `exported access log` with the date range and the names of
the filters used, never their values.

## Follows

- Counsel must review the Business Associate Agreement's amended return-or-destroy clause and the
  matching Terms and Privacy text.
- Infrastructure (owner): S3 Object Lock in governance mode with 7-year retention on the documents
  bucket and no expiry of current or noncurrent versions or `ses-retained/` before 2557 days (raw mail
  waits in a separate inbound bucket until the worker keeps it there, [0046](0046-email-intake.md)); AWS Backup monthly snapshots kept 7 years; CloudWatch log groups kept 7 years (2557 days);
  CloudTrail; the migrate task on `MIGRATION_DATABASE_URL`, api and worker on the `bodha_runtime`
  `DATABASE_URL`; `APP_VERSION` from the image tag; the intake function allowed to put under
  `ses-retained/`.
- Migration 0015 follows 0011 to 0014 (spend, tours, the review audit trail, multi-practice membership)
  and covers their tables: the review records and `auth_events` are append-only under the same triggers
  (0013's update-only guard is replaced, and restored on downgrade), `practice_memberships` is never
  deleted, `analyses.cost_microusd` and `price_snapshot` are written once, and `bodha_purge_practice`
  removes them in foreign-key order, keeping the accounts of people who belong to another practice.
  `auth_events` has no chain of its own: every event of a known person is also written to that person's
  practices' access logs or HQ activity, which are chained; a failed sign-in for an unknown email is
  only in `auth_events`. A later migration that adds a table holding practice data must add it to
  `bodha_purge_practice` (a missing one makes the purge fail on a foreign key, never skip it); tables
  that exist when 0015 runs get SELECT, INSERT and UPDATE (append-only ones no UPDATE), and one the
  runtime must delete from needs an explicit grant.
- Closing a practice also ends its memberships; approved claim snapshots, exports, statements and
  comments stay. HQ cannot appoint an admin to, renew or edit a closed practice.
- A practice purge builds the access-log archive in memory and runs in the HQ request; a practice with
  millions of entries would need it streamed or run as a task.
