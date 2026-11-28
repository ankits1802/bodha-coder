# 0049 Claims to a clearinghouse as X12 837P, beside the claim lines CSV

Date: 2026-11-28

Context: billers took claim lines out of Bodha as CSV or JSON and keyed or loaded them somewhere else.
The owner asked for claims to go straight to the practice's clearinghouse as ASC X12 005010X222A1
(837P), built from the approved claim snapshot, with the CSV download kept as it is, a per-practice
SFTP connection stored encrypted, a download for practices that upload by hand, 999 and 277CA
acknowledgments read by the worker, each claim's status on Billing with a way to fix and resend, and
every file and acknowledgment kept as its own append-only record.

## Choices

**Our own writer, parser and validator, no X12 library.** The X12 packages for Python are either
unmaintained, generic (no 837P loop rules) or large frameworks. The envelope reader already existed for
835s (`services/x12.py`). `services/x12_writer.py` writes segments with the separators `* : ^ ~` and the
basic character set (names and addresses upper case, anything else a space), `services/claim_837.py`
writes the loops from plain dataclasses, and `services/claim_837_check.py` reads the finished text back
and checks it independently of the writer: envelope and counts, the HL hierarchy, required segments and
elements, lengths, NPI check digits, EIN, ZIP, state, dates, code shapes, pointers and CLM02 against the
lines. A file that fails is never stored or sent. Clearinghouse companion guides add their own rules on
top of the implementation guide; the first test files are where those show up (below).

**Paramiko for SFTP, behind one adapter.** `adapters/sftp.py` is the only module that touches the
network. Paramiko 5.1.0 (with invoke and PyNaCl) is current and maintained; `asyncssh` was the
alternative and would have been a second async stack for one adapter. Every operation opens and closes
its own session; the poll downloads a folder's new files in one session. The adapter refuses a host
that resolves to anything but public internet addresses and connects to the address it checked, so a
practice admin cannot make the API or worker reach the VPC or the instance metadata service.

**The host key is pinned at setup.** Read host key returns the server's key as OpenSSH prints it
(`SHA256:` and unpadded base64) for the admin to compare with what the clearinghouse publishes; saving
stores it and every later session checks it before signing in. A rotated key at the clearinghouse stops
sending until an admin confirms the new one, which is the point.

**The password or key is sealed with its own key.** `core/secret_box.py` is the Fernet code that sealed
two-step secrets, made general; two-step secrets keep `MFA_ENCRYPTION_KEY` and clearinghouse secrets use
`CLEARINGHOUSE_ENCRYPTION_KEY`, so one key's loss or rotation does not touch the other. The sealed value
is never returned: the view says whether one is saved, and saving again without a new one keeps it while
host, port, user name and sign-in kind stay the same. Only unencrypted private keys are taken, since a
passphrase would have to be stored beside the key anyway. Host, user name and folders stay readable, as
they identify the connection to the admin and are not secrets. Connections are rows written once; a
change is a new row and the old one is retired, so the record of who pointed claims where is kept.

**Control numbers rise per sender.** ISA13, GS06 and ST02 carry one number per file, the highest used by
the same sender qualifier and id plus one, under an advisory lock on the sender and a unique constraint,
across practices that happen to share a submitter id. BHT03 is the file's id without dashes, which a
277CA returns in the information receiver's TRN02, so its claims link to the exact file. CLM01 is the
first 20 characters of the note id in capitals: the claim reference payers echo in CLP01 of an 835 is
then the prefix the remittance matching already uses, and a 277CA claim links by it within its file.

**Which data the file uses.** Codes, modifiers, units and pointers come only from the latest
`approved_claims` snapshot, through the same `claim_lines.build_claim` as the CSV, so the two exports
cannot disagree. Patient and subscriber facts come from `claim_details`, a revision a biller confirms per
claim. Practice details, payers, providers and charges are settings read when the file is built; the
file itself, stored with its SHA-256 under `practices/{practice}/claim-files/{submission}.x12`, is the
frozen record of what was sent. Billing provider: the practice by default (group NPI from the provider's
details or the practice, EIN, practice taxonomy), or the provider for one who bills as an individual;
a group claim names the provider as rendering provider. Service location is the billing address (no
2310C) and frequency is always 1.

**Minimal patient data, confirmed by a person.** `claim_details` holds only what an 837P needs for the
patient (name, birth date, sex, address), the relationship, member id, group number and, when the patient
is not the subscriber, the subscriber's name. Nothing is saved without a person: the first read suggests
the birth date and sex the note holds and the name as read, and every field of an earlier confirmed claim
for the same name and birth date. The note's name is never split into last and first, because a file name
puts the last name first and a page label does not, and the note does not record which it came from.
These facts never go into object keys, file names, logs, access-log details or inbox payloads.

**The payer stays on the note.** A claim's payer is `notes.payer`, as for claim checks, with its change
history; billers may now set it (`PAYER_SETTERS`). A payer's SBR09 claim filing code defaults from its
plan type (commercial CI, Medicare MB, Medicare Advantage 16, Medicaid MC) and is chosen for `other`.

**Charges are a schedule in Setup.** One charge per CPT or HCPCS code in `practices.setup`, times units on
the line. Modifier-specific charges (26, TC) are not modelled; a practice that needs them sets the charge
it bills most often and corrects the rare claim at the clearinghouse.

**Sent means exported; rejected means ready again.** A delivered or downloaded file marks its notes
exported, so the claim lines CSV, untouched, never offers them again, and a claim exported as CSV is never
sent. A failed delivery leaves them ready. A 999 or 277CA rejection returns the note to approved and
unexported when that file is still its latest, so it reappears in Ready to bill with the reason, can be
reopened by a coder when the codes are wrong, and goes out in a new file with the next control number.
A file stored but with no delivery row after ten minutes counts as failed.

**Statuses from category codes, reasons from the guide's tables.** Accepted: 277CA categories A0, A1, A2,
A5, and 999 status A or E. Rejected: A3, A4, A6, A7, A8, E0, E3, E4, action code U, and 999 R, M, W, X.
Anything else is pending. The 999 segment, element, transaction and group error descriptions are in
`codes/x12_codes.py`; the roughly 900 claim status codes (507/508 lists) are not vendored, so a reason
shows the category in words, the status code number and the payer's free text (STC12).

**The poll.** Every ten minutes, one worker at a time (`core.db.exclusive_job`), each current SFTP
connection of an open practice: list the response folder, skip files older than the connection by more
than a day and names already fetched (kept as SHA-256 so a remote name never sits in the database), fetch
at most 50, store each as received, read 999s and 277CAs, and keep anything else as `other` or
`unreadable`. Remote files are never deleted or moved; clearinghouses age them out themselves. A biller
may upload a 999 or 277CA by hand, which is the only way responses reach portal practices.

**Roles and records.** Billers and admins send, download and upload responses; admins manage the
connection and the charge schedule. Every action writes the practice's access log; the worker writes as
`Bodha (clearinghouse)`. Connections are written once; claim details, submissions, items, deliveries,
response files and acknowledgments are append-only, with database timestamps, granted to the runtime
role without UPDATE (connections with UPDATE for retiring only) and never DELETE, and removed only by a
practice purge (migration 0022).

**The clearinghouse is the practice's vendor, not Bodha's subprocessor.** The practice chooses and
contracts its clearinghouse and enters its own credentials; Bodha transmits claims there at the practice's
direction, as the practice's business associate preparing its claims. The clearinghouse is the covered
entity's own business associate (or a covered entity itself), under the practice's agreement with it, so
it does not go on the subprocessors page. The legal pages were read for anything this makes untrue and
none was found: the BAA's permitted uses list claims exports among non-exhaustive examples of the
Service, the privacy policy covers sharing at the customer's direction, and the Terms already leave
claims and their submission to the customer.

## What follows

- Before the first file a practice fills in Practice details (with ZIP+4), payer ids, provider NPIs,
  charges for the codes it bills and the clearinghouse (ids, test or production, portal or SFTP), and a
  biller confirms each claim's patient and subscriber details. Start in test (ISA15 T).
- Nothing has been sent to a real clearinghouse. Office Ally, Availity, Claim.MD and Waystar each publish
  a companion guide (receiver ids and qualifiers, ISA14, file naming, folder names, whether 2010BB
  needs the payer address, whether billing provider taxonomy is required). The first test files will show
  which of those this writer needs; record each in a short decision when it is made.
- Not covered: secondary and tertiary payers (COB loops 2320 and 2330), corrected and voided claims
  (frequency 7 and 8 with REF*F8), referring providers, prior authorization numbers, a service location
  other than the billing address, ambulance and other loop-specific data, modifier-specific charges, and
  TA1 interchange acknowledgments (ISA14 is 0).
- `CLEARINGHOUSE_ENCRYPTION_KEY` is a new Secrets Manager secret made by OpenTofu and given to `api` and
  `worker`; its rotation is in `docs/OPERATIONS.md`. A clearinghouse that allows SFTP only from listed
  addresses needs the NAT gateways' Elastic IPs.
