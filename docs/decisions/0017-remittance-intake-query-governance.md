# 0017 Remittance loop, automatic intake and query governance

Context: practices asked to see what payers did with the claims Bodha approved, to stop uploading
PDFs by hand, and to show that provider queries follow the AHIMA/ACDIS compliant query practice
(2026 draft, Section XI). Migration 0005 had already created `remittances`, `remittance_lines`,
`practices.intake` and `addendum_requests.escalated_at`.

## Choices

**Our own strict X12 reader, no dependency.** Bodha needs a small subset of one transaction (835);
a reader of about 300 lines that we own costs less than a dependency's object model, release cadence
and review, and no library was evaluated as clearly better. `services/x12.py` takes the separators from the fixed-width ISA,
checks every envelope (nesting, control numbers, counts) and `services/remittance_835.py` refuses a
line or payment that does not balance. A file we cannot read exactly is refused with the segment
named, never half-read.

**SVC01 is the paid code.** The X12 835 implementation guide puts the adjudicated code in SVC01 and
the submitted code in SVC06 only when the payer changed it. Billed = SVC06 or SVC01, paid = SVC01;
the request to treat SVC01 as billed was read against the standard.

**One `remittances` row per payment.** An 835 file can hold several ST/SE transactions (one per
check or EFT), each with its own payer and date; each becomes a row and all share the stored file.

**Matching fails closed.** CLP01 matches a note id (exports carry it; payers may return only 20
characters, so a unique prefix of at least 8 counts) only when the date of service agrees. Otherwise
patient name tokens, date of service and billed CPT must point at exactly one note. Anything else
is `unmatched`; an unmatched denied or downcoded line still gets its appeal-by date.

**Status.** Denied means CLP02 = 4, or nothing paid with nothing left to the patient (a visit that
went to the deductible is paid as billed). Downcoded means a lower level of the same E/M family, or
CO-150/CO-152 (level or length of service not supported). The schema's `matched` status is used for
a matched line paid under some other code or reversed, shown as Other.

**Appeal windows per plan type.** Medicare redetermination is 120 days from the remittance; the rest
default to 180. The plan type comes from CLP06 (MA/MB Medicare, MC Medicaid), then the practice payer
list, then commercial. Admins can change the windows (`practices.setup.appeal_days`); stored
appeal-by dates are not recomputed. The appeal letter is a plain-text draft that points to the
defense packet; a biller edits and signs it.

**Intake reuses the upload service.** `create_upload` needs a user, so intake uploads as the
practice's first active admin with user agent `bodha-intake`; the activity entry says it was intake.
Each file is checked with the upload checks before the batch, so one bad file is rejected alone.

**Intake locking.** Several workers may poll at once. `create_upload` commits per batch, which would
release a transaction lock held on the session, so the per-practice advisory lock is taken on a
separate connection from the session's engine and held until the practice is done; a second worker
skips that practice. Escalation locks the request rows with `FOR UPDATE SKIP LOCKED` and commits once.

**PHI in keys.** Dropped files are named by the practice and may carry a patient name. Bodha moves
them within a poll to keys named by the SHA-256 of the content; the reason file holds the original
path. DEPLOY-INTAKE.md asks practices to drop files without patient names where they can (the
model reads the patient from the note).

**Repeat queries.** A key asked on a note (sent, answered or expired; not cancelled) blocks the same
key until the note has a new text revision other than the addendum that request produced. The rule
lives in `query_governance.py`, which does not import `addenda`, so `addenda.create_request` can
call it without a cycle; the metrics, which need the answer vocabulary, are in `query_metrics.py`.

**Agree rate.** Non-leading queries offer no preferred answer, so an answer agrees when it is one of
the specific clinical options rather than No, Clinically undetermined or Other.

## Follows

- The worker calls `poll_intake` every minute and `escalate_unanswered` every hour, and
  `addenda.create_request` calls `refuse_repeat_queries`.
- Changing an appeal window moves every appeal-by date (amended 2026-11-27, below); lines stored
  before migration 0007 keep their stored date.
- `adapters/object_listing.py` lists through `S3ObjectStore`'s paginator helper; if that helper
  moves, the listing moves with it.

## Amended 2026-11-27

**Repeats are found by checksum.** `remittances.file_sha256` (migration 0006) holds the SHA-256 of
the file; a file whose checksum matches an earlier upload of the practice is refused whatever its
name, and the message names the earlier upload's day and file name. The check runs under a
per-practice advisory lock so two uploads of one file cannot both pass. Payments stored before the
column are given their checksum from the stored file before the check.

**Appeal dates are computed when read.** A line stores the plan type whose window applies
(`remittance_lines.appeal_plan_type`, migration 0007, appealable lines only) and no date; list,
detail and letter add the practice's current window to the payment date. The plan type was not
stored before, and the alternatives were worse: re-reading every 835 on each list costs a storage
read per file per page, and inferring the plan type from the stored date is ambiguous whenever two
windows are equal. The `appeal_by` write stops; the column stays for lines stored before 0007,
which keep their date because their plan type cannot be recovered without reading the file.

**Intake is uploaded by the system.** `uploads.create_intake_upload` writes `batches.source`
`intake` with no `created_by`, billed code sets with no actor, and the access entry through
`audit_log.record_system_access` as `Bodha intake` (actor id `bodha-intake`). The access-log check
allows only `user` and `provider`; adding `system` needs a migration and a change to the shared
access-log type and screen, so the kind stays `user` and the actor id shows it is not a person, as
for `Bodha (auto)`. Upload history shows Intake.

**Checksum names on arrival.** The first poll that sees a dropped file renames it in its folder to
the SHA-256 of its content, ` - <CPT>` when the name carried a CPT code, and its suffix, before
any check, so a patient name in a file name lives at most one poll even when reading the file
fails. The CPT code is the only fact intake takes from a name and is not PHI, so it rides in the new
name and survives a failed poll. The original name is kept nowhere: intake notes carry the checksum
name and reason files name the renamed path. This replaces "the reason file holds the original
path" above.

**Email intake function.** `infra/ses_intake/handler.py` takes the recipient from the object key
(`ses-inbound/<recipient>/`, set by the per-address receipt rule), because the envelope recipient
is not reliably in the message headers. It requires every SES spam and virus verdict header to be
`PASS`, a single `From` address on the inbox's sender list (the list is required) and a date of
service in the subject; without a date it writes nothing rather than guess the date of service. It
names PDFs by their checksum and deletes the raw message.

## Amended 2026-11-28

**Email intake is replaced.** The function no longer maps recipients, checks senders or writes PDFs: it
records each message's envelope and SES verdicts beside the stored message, and the worker checks the
practice's own address and allowed senders, matches each PDF from page 1 and records every message
([0046](0046-email-intake.md)). The paragraph "Email intake function" above describes the earlier design.
