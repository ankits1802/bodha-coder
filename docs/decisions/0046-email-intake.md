# 0046 Email intake: an address per practice, checked by the worker

Date: 2026-11-28

Context: practices that can only email or forward visit notes had no way in. The function in
`infra/ses_intake` mapped fixed recipients to watched folders from an environment variable, nothing
deployed it, and the app had no setup for it. The owner asked for an address per practice that the admin
sets up in Settings, an allow-list of senders, refused mail recorded and never read, the same checks and
page-one matching as a drop upload, an append-only record of every message, and the watched folder kept.

## Choices

**A subdomain with its own MX record.** Mail goes to `intake.<domain>` (`email_intake_subdomain`), whose
only record is `MX 10 inbound-smtp.us-east-1.amazonaws.com`. The apex keeps its Microsoft 365 records.
The parent domain is already a verified SES identity, which covers the subdomain.

**One receipt rule for the whole subdomain.** Addresses are made and retired in the app, so a rule per
address would make the API manage SES. The rule (`bodha-staging-intake` in the rule set of the same name)
matches the domain, requires TLS, has SES scan for spam and viruses, stores the raw message at
`ses-inbound/<message id>` through a role that may write only there, and then invokes the function.

**Mail lands in its own bucket.** SES cannot deliver into a bucket whose Object Lock has a default
retention period, and the documents bucket keeps every object seven years by default, so creating the
rule failed with "Unable to write to S3 bucket". Object Lock cannot be removed from a bucket, and the
documents bucket must keep it. Raw mail and envelopes therefore land in
`bodha-staging-mail-inbound-<account>`: no Object Lock, no versioning, the documents key, TLS only,
public access blocked, and anything unread expires after 14 days (`inbound_days`). Nothing is kept there:
the worker reads each message from that bucket, keeps the copy under `ses-retained/` in the documents
bucket (seven years under Object Lock) before it records or files anything, and then deletes the inbound
objects. Seven-year retention therefore holds for every message Bodha handles; the only mail that never
reaches the documents bucket is mail that sat unread for 14 days, which means the worker was down and the
alarms already fired. `EMAIL_INTAKE_BUCKET` names the bucket for the worker; when it is empty the worker
reads `ses-inbound/` in the documents bucket, as tests do.

**The function writes only the envelope.** The envelope recipient is not reliably in the headers (0017),
and SES verdicts in headers can be forged by a sender. SES hands both to the Lambda action, so
`handler.py` writes `ses-inbound/<message id>.json` (version 1: message id, received time, recipients,
spam, virus, SPF, DKIM and DMARC verdicts) and nothing else. Its role may put only `ses-inbound/*.json`
in the inbound bucket and use the documents key; it reads no mail. The earlier mapping, subject date and folder writing are
gone.

**The worker decides.** `services.email_intake.poll_email_intake` runs every minute under one advisory
lock. For each envelope it copies the raw message to `ses-retained/<message id>` first, parses it with the
standard library, records one `intake_messages` row per address it was sent to, commits, and deletes the
message and envelope from the inbound bucket. A message that fails is logged and left for the next poll; one bad message must not stop the
others, and the error log reaches the alarms and error tracking.

**Refusals, in order.** Unknown address (recorded without a practice or sender), a test message (below),
a retired address, a practice that is not open, a failed spam or virus scan, DMARC not `PASS`, a sender
not on the list, no PDF, more than 50 files. DMARC is required because the `From` address is what the
allow-list trusts and DMARC is what ties it to the sending domain; a domain without DMARC is refused as
"sender not verified" rather than trusted. A whole public mail domain (gmail.com and the others in
`services.email_domains`) cannot be allowed, only its addresses.

**Files go through the upload path.** Each attachment is renamed to its checksum name
(`intake.arrival_name`, keeping a CPT code from the original name), checked with the upload checks,
and matched from page 1 with `upload_matching.match_file`, the date from the original attachment name
counting as it does for a drop. A file is accepted only when the provider and the date of service are
each at least `CHECK_BELOW` (0.8); the place is the matched one or the intake place of service. Accepted
files become one batch per provider, date and place through `uploads.stage_intake_upload`, in the same
transaction as the message record, so a record never names a note that was rolled back. Refused files are
kept only in the retained message; the admin sees why each was refused, never a file name.

**Addresses.** Sixteen base32 characters from 80 random bits. A new address retires the current one
(`retired_at`, kept; history shown), turning email intake off retires it without a successor, and mail to
a retired address is recorded and refused. Addresses, senders and tests are written once per column
(`bodha_write_once`); messages are append-only.

**The test is sent by Bodha.** Send a test emails the current address from `MAIL_FROM` with
`Bodha intake test <test id>.<token>` in the subject; only the SHA-256 of the 128-bit token is stored.
A message whose subject carries a matching, unanswered reference for that address marks the test arrived
and is recorded as `test`; nothing in it is read. It proves MX, the receipt rule, the function and the
worker end to end. The practice's own scanner is checked by sending to the address and reading the list.

**Off until applied and live.** `EMAIL_INTAKE_DOMAIN` reaches the api and worker only with
`email_intake_live`, which also activates the rule set; the app answers `available: false` and refuses
to issue addresses until then.

## Follows

- Only one SES receipt rule set can be active in a region and account. The account is shared, so before
  `email_intake_live` the operator checks `aws ses describe-active-receipt-rule-set`; if another rule
  set is active, activating ours would switch it off, and that is a decision for the owner, not Bodha.
- SES receipt-rule actions take no resource-level permissions, so the operator's `SesReceiving` grant is
  on `*`; the function actions are limited to `function:bodha-*`.
- Messages to unknown addresses have no practice, are never purged with one and are kept like other
  records. `bodha_purge_practice` removes a practice's addresses, senders, tests and messages.
- The 0017 paragraph "Email intake function" is replaced by this record.
