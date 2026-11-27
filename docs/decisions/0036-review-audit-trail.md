# 0036 Review audit trail

Date: 2026-11-28

Context: an auditor asking why a claim was billed as it was could see Bodha's suggestions and the
choices people made, but not why a person departed from Bodha, what exactly was approved and exported,
what a provider was shown when asked, or the discussion behind a decision. The owner's rule stands: every
model run, suggestion, decision, code-set change and note-text revision is its own record, and nothing is
overwritten or deleted.

## Choice

- **Override reasons.** A choice departs from Bodha when it turns down a proposed change (keep or skip on
  a lower, raise, replace, add or remove of a visit level, diagnosis, procedure or modifier) or keeps a
  billed code Bodha flagged (keep on an ask or review finding that names a billed code). The rule lives in
  `services/override_reasons.py`; the note view sends each finding's `departing_choices` so the screen
  never re-derives it. The six reasons are fixed (`models.OVERRIDE_REASONS`); Other needs a note, any
  note is at most 500 characters, and Postgres checks both. A reason is stored on the decision row
  (`override_reason`, `override_note`, `actor_role`); a reason given later is a new decision row with the
  same choice, so nothing is updated. Hand edits of billed codes and of diagnosis pointers cannot be
  saved without a reason (422); the code-set row and the pointer decision rows carry it. Approval answers
  409 while the latest decision on any current finding departs without a reason. There is no setting to
  turn this off. A compliance keep without a structured reason is stored as Other with the written
  reason as its note. Pointer decisions written before this change carry no reason and do not block
  approval; they predate the rule.
- **Approved claim snapshots.** Approval, including auto-approval, writes an `approved_claims` row next to
  the final code set: the claim with every procedure line's pointers resolved (stored choice, add-on
  primary or first four diagnoses, frozen so a later NCCI release cannot change it), the E/M line, the
  diagnoses with their letters, the billed codes as uploaded and as reviewed, every decision with its
  reason, the approver (id, name, role, or Bodha (auto) as `system`) and time, and the provenance
  (analysis, model, prompt version, the note text revision ids read, the document key and its SHA-256).
  Reopening and approving again adds revision 2. Migration 0012 backfills one snapshot per note already
  approved or exported from its latest final code set, marked `backfilled`.
- **Exports read snapshots.** The billing list, the claims CSV and the claim lines read the latest
  snapshot, never the live code sets. Every export (`claim_exports`: format, who, role, when, address,
  device) lists its notes and snapshot revisions (`claim_export_items`) and stores the exact bytes under
  `practices/{practice}/exports/{export}.{csv|json}` with their SHA-256; `GET
  /api/billing/exports/{id}/file` serves them again after checking the hash. The claim lines download now
  marks its notes exported, like the CSV.
- **Provider confirmation of level changes.** A practice setting (`practices.confirm_level_changes`,
  `hold_until_confirmed`, both off) asks the provider to confirm when the approved E/M code differs from
  the billed one. It reuses the provider request: an `addendum_requests` row with `purpose`
  `level_change` and the snapshot id, so tokens, codes, channels, reminders, expiry and escalation are
  the existing ones. The provider sees the billed and approved levels and the visit-level evidence
  quotes; the text shown is stored with the answer. Confirming releases a hold; disagreeing needs a
  comment, reopens an approved note and emails the approver a link with the practice name only. With
  hold on, a note whose latest snapshot has a level request sent or expired cannot be exported (409 when
  named, left out of export all). Reopening cancels a pending request.
- **Provider statements.** Every addendum signature and level answer writes a `provider_attestations` row:
  the exact wording the provider ticked (sent by the server and echoed by the page; a page showing other
  wording is refused with 409), that it was ticked, the note text revision ids shown, the text they
  signed or were shown, their answer and comment, the address and the device. Each six-digit code check,
  accepted or refused, is an access-log row with the address and device and never the code.
- **Comments.** `review_comments` holds threads on a finding key or the note; a removal is a separate
  `review_comment_removals` row (who, role, when), so removal hides a comment from the default view and
  keeps it; admins and compliance can show removed comments. Only the author or an admin removes. A
  mention names an active practice member who can open notes and emails them the practice name and a
  link to the note's History.
- **Append-only in the database.** A trigger refuses UPDATE on approved claims, exports and their items,
  provider statements, comments, removals and audit packages. Deleting a note or a practice still
  deletes them with the rest of its records.
- **Audit package.** Admins and compliance download a ZIP per note: the defense packet, every stored PDF
  revision, every text revision, every analysis with its report and raw reply, every suggestion of every
  run, decisions, code sets, snapshots, provider requests and statements, comments, exports and the
  note's access-log rows, with `manifest.json` listing each file's SHA-256. The ZIP is stored under the
  note's folder with its hash in `audit_packages`, and the download is logged. An export file is included
  only when the export held this visit alone; otherwise the package lists the export and its file hash
  and withholds the file, because it holds other patients' visits (HIPAA minimum necessary).
- **Defense packet.** It now carries the note text, the suggestions not followed with their reasons,
  suggestions of earlier runs, flag and compliance reasons, snapshots, exports, provider statements and
  comments.

## Follows

- Approving needs a messenger: approval may send a level request in the same transaction, and a provider
  without a usable contact makes such an approval fail rather than skip the request.
- Code that adds a table keyed to notes adds it to `note_changes.CHILD_TABLES` and
  `records._delete_practice_rows` in foreign-key order.
- Export and package keys are of a shape the orphan sweep does not know, so it leaves them alone.
- Mentionable people are read from `users.practice_id`; multi-practice membership will need to read them
  from its membership table.
