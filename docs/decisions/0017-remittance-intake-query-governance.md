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
- Changing an appeal window does not move appeal-by dates already stored.
- `adapters/object_listing.py` lists through `S3ObjectStore`'s paginator helper; if that helper
  moves, the listing moves with it.
