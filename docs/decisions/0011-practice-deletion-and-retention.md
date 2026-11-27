# 0011 Replaced PDFs, access-log retention and deleting a practice

Context: practices need to swap a note's PDF for an amended one, keep the access log only as long
as the law and their policy require, and leave Bodha entirely; HQ needs to administer practice
admins and renewals; setup needs provider credentialing and a real payer list.

## Replaced PDFs

- A replacement is a new document revision, not an edit. The new PDF gets its own key
  (`document-r{n}.pdf`, `n` being its `note_texts` revision) and becomes `notes.file_key`; the old
  PDF and its text stay, because they are part of the record that was coded.
- A read uses the texts from the latest `document` revision onward. Addenda signed against an
  older document are not mixed into the new one; the amended PDF is expected to carry them.
- A scan has no text layer, so its `document` revision is an empty string. The read sends the PDF,
  and the model's extracted text is stored as the next `document` revision, exactly as for a first
  scanned upload, so later reads (addenda, visit type changes) use that text.
- Refused for an exported note (the claim left Bodha), a note being read (a run is using the old
  text), and while a provider request is open (its questions are about the old document). The same
  file or a file another note already holds is refused, as at upload.
- Queued analyses of the note are superseded so only one read of the new document runs; an approval
  is cleared because the codes were approved against the old document.

## Access-log retention

- `practices.access_log_years`, 6 by default, at most 10, chosen by the practice admin. HIPAA asks
  for six years of documentation (45 CFR 164.316(b)(2)); some states and payers ask for more.
- The cutoff is the start of the practice-local calendar day that many years before now, so a row
  is kept for whole days in the practice's own time zone. The worker runs the purge once a day.
- The purge deletes rows; there is no archive. A practice that must keep longer chooses 10 years.

## Deleting a practice

- HQ only, in two steps: the practice must first be ended or blocked (everyone signed out), then the
  delete names the practice exactly. A typed name in a danger dialog guards against the wrong row.
- Every row that belongs to the practice goes, in foreign-key order: note children, addendum
  requests, analyses, code sets, notes, batches, providers, MIPS list, access log, activity, the
  users' tokens, sessions and recovery codes, users, the practice. Its activity rows go too because
  practice admins wrote them and they name the practice's people.
- One `activity` row `practice deleted` (practice id and name, who, when) is written after the
  delete and survives: HQ keeps the fact that the practice existed and who removed it.
- Stored objects are removed after the commit, by listing every key under `practices/{id}/`
  (`list_objects_v2` pages) and deleting them in batches of 1000. If that fails the records are
  already gone, so the failure is logged and the objects are orphans; see TECH_DEBT "Stored files can
  outlive their notes". `delete_prefix` refuses any prefix that does not end in `/`.

## HQ administration and paging

- A practice row shows its first admin: the earliest admin who is not blocked, or the earliest one
  when all are. The admin link resends an invite to an invited admin and sends an active admin the
  password reset email used by Team; a blocked admin gets nothing.
- Renewal adds one year to the later of today (practice time zone) and the current renewal date, so
  renewing early never shortens a plan and renewing late does not back-date it.
- Lists that grow without bound page on the server with `offset` and answer `total`: uploads 50,
  billing 100 (the export still takes up to 500 rows), HQ activity 100 with server-side practice and
  action filters, the access log 200.

## Credentialing and payers

- Provider credentialing lives in `providers.details` (JSONB, migration 0004): NUCC taxonomy code
  (10 characters, letters and digits, ending in X), state license number with its state, DEA number
  (two letters and seven digits with the DEA check digit), whether claims go under the provider's
  own NPI or the group NPI, the group NPI (NPI check digit), the supervising physician and whether a
  signature is on file. CSV import takes the same names as extra columns.
- The payer list replaces the free-text "Contracted payers" field of the Insurance payers section:
  `practices.setup["payers"]["list"]`, each with a stable id, a name unique in any case, an optional
  payer ID (2 to 15 letters, digits or hyphens), a plan type (commercial, Medicare, Medicaid, other)
  and active. A value already typed into the old field stays stored but is no longer shown.

## Follows

- `services.analysis.run_analysis` stores model-extracted text at the next text revision instead of
  revision 1.
- Note deletion removes every key under the note's folder (`practices/{p}/notes/{n}/`).
- The provider's answer page shows every note text; it should show the texts from the latest
  document onward, as the note view does.

## Amended 2026-11-27: the orphan sweep

A file can outlive its record: the database can fail after a file was stored, and removing a deleted
note's or practice's files can fail after its rows are gone. Once a day the worker lists every
practice folder and deletes objects older than 24 hours that no row holds (current and earlier
document revisions, analysis replies, remittance files, evaluation replies of a case in its run).
It deletes only keys whose shape it knows and leaves the intake folders to the poller; a folder of a
practice with no row is emptied only when HQ activity records its deletion, so a database that
lacks a practice never empties that practice's folder. Twenty-four hours is longer than any read
or upload takes, so a file stored a moment before its row is committed is never taken for an orphan.
