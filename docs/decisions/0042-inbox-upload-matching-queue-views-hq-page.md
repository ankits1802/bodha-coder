# 0042 Inbox, upload matching, queue views and the HQ practice page

Date: 2026-11-28

Context: the measured workflow baseline found that nothing tells a person when a provider answers, an
asked request expires or someone mentions them; that uploading notes for two providers on two dates took
about 37 clicks because a batch is one provider, one date and one place; that the provider lane hides
two different states (questions not yet sent, and waiting on the provider) and the queue sorts only by
due time; that HQ had no practice page, no list of a practice's people, no search, and a spend list that
left out practices with no priced use; and that billers saw two exports that produced different files.

## Choice

- **An inbox per person and practice.** `inbox_items` holds the recipient, the practice, a `kind` from a
  fixed list (`provider_answered`, `level_disagreed`, `request_expired`, `mentioned`,
  `training_assigned`, `payment_failed`, `plan_ending`, and `compliance_returned`, kept in the list for
  the compliance return that a later change writes), the note id when there is one, the actor's name and
  id, a payload, `created_at` and `read_at`. Every writer calls one function,
  `services.inbox.notify(db, practice_id, user_ids, Notice)`, inside the writer's own transaction, so the
  item and the change it reports commit together. `notify` writes only for people with an active
  membership in that practice (decision [0037](0037-multi-practice-membership.md)), and reading filters
  by the person and the session's active practice, so an item of one practice is never shown in another.
- **No PHI in a payload.** `checked_payload` allows only the keys listed for each kind in `PAYLOAD_KEYS`
  (a question count, a request purpose, a comment id and whether it sits on a finding, a training run
  id and note count, a date) and strings of at most 64 characters; anything else raises. The patient
  name and date of service shown in the list are joined from the note when the list is read, by a note
  reader, and the read is written to the access log as `listed inbox`, as the queue listing is. Opening
  an item opens the note through the normal permission-checked note route.
- **Writers.** The provider signing an addendum tells the person who sent the request; a level
  disagreement tells the approver of the snapshot (the email stays); the expiry job tells the asker; a
  mention tells each person named other than the author (the email stays); drawing a training set tells
  each trainee with the run id and how many notes, never which notes (a blind audit draw writes nothing:
  its reviewers must not learn which notes they hold from anywhere but the blind form); a subscription
  that becomes past due tells every active admin once; and a plan without a live subscription that ends
  within three days tells every active admin once per end date (`notify_plans_ending`, hourly from the
  worker). The three days is `PLAN_ENDING_DAYS`; the plan screen now reads `ending_soon` from the server
  so the banner and the inbox share the threshold.
- **The unread count is polled, not pushed.** `GET /api/inbox/count` answers one indexed count; the
  sidebar asks on each navigation and every two minutes while the page is visible. A session claim was
  not chosen because the count changes between refreshes, and a push channel was not worth a new
  dependency.
- **Upload matching reads page 1 with rules, not the model.** `POST /api/uploads/preview` now takes the
  PDFs. For each one `services.upload_matching` reads the first page's text: a valid NPI of an active
  provider (0.99), a provider's first and last name (0.9) or a surname shared with no other provider
  (0.6); a labelled date of service in the usual formats (0.95, 0.99 when the file name agrees, 0.6 when
  it disagrees), else the file name's date (0.85), else the first date on the page that is not a birth
  date and not in the future (0.5); a labelled place of service by code or name (0.95), else the
  matched provider's usual place (0.8); a labelled patient name (0.9), else the file name's (0.85). A
  file's confidence is the weakest of provider, date and place, and below 0.8 the row is marked Check.
  No model call is made, nothing is stored, and the preview writes `previewed uploads` to the access log
  because it reads patient names. Files whose bytes another note already holds are marked as uploaded.
- **The server makes the batches.** `POST /api/uploads` takes per-file provider, date and place in
  `details`, with the old form fields kept as defaults so intake, the load test and older clients work
  unchanged. `grouped_files` makes one batch per provider, date and place, in the order first seen;
  every file is checked before anything is stored, so a file without a placement refuses the whole
  upload. The answer adds `batch_ids`; `batch_id` stays the first. The SHA-256 duplicate refusal and email
  intake are unchanged.
- **Dollar impact is stored at placement.** `refresh_placement` derives the claim from the current
  findings and choices and stores `notes.impact_cents`, the Medicare national estimate of that claim
  minus the billed codes, or null when neither side can be priced. It follows every decision because
  placement runs after each. `GET /api/notes?sort=impact` orders by its absolute value, largest first,
  with unknown impact last; notes placed before this change get theirs at their next placement.
- **Queue views.** Built-in views are defined on the server per role (coder My work, CDI Questions to
  send, admin Unassigned and Overdue, compliance Flagged) so the filters have one home; saved views are
  rows in `queue_views` per person and practice (at most 20, names unique ignoring case). A view is a set
  of queue filters: lane, lane reason, assigned, provider, overdue and sort. The provider lane is shown
  as two views by `lane_reason`, with counts in `provider_reasons` on the queue page and on Today.
- **The HQ practice page.** `/hq/practices/{id}` reads `GET /api/hq/practices/{id}` (the same row as the
  practices list, and the places the practice uses) and `GET /api/hq/practices/{id}/people` (live
  memberships with role, status, two-step and last active), and reuses the renew dialog, the add admin
  dialog, the spend route with `practice_id`, and HQ activity filtered to the practice. `GET
  /api/hq/search` matches practice names and practice-account emails and names (HQ accounts are not
  searched; they have the HQ team page), wildcards escaped through the shared `core.text_search`.
- **Spend lists every practice.** The spend report adds practices with no analyses in the range at zero
  after the rest, so a quiet practice is visible and the practice page always has its row.
- **One biller export.** The billing screen offers one "Export claim lines" action with CSV by default and
  JSON as an option. It marks the visits exported and is recorded as a claim export with its stored file
  (decision [0036](0036-review-audit-trail.md)). The stored files remain downloadable from Exported. The
  claims CSV route stays for API clients and the audit trail tests; the screen no longer offers it.

## Follows

- Migration 0016 adds `inbox_items`, `queue_views` and `notes.impact_cents`, adds both tables to
  `bodha_purge_practice` (decision [0038](0038-seven-year-retention-and-tamper-evidence.md)) before the people leaving with the practice, and gives the
  runtime role `UPDATE` on both tables and on `notes.impact_cents` and `DELETE` on `queue_views` (a saved
  view is a preference, not a record) when the role exists.
- A later "compliance returned" writer calls `notify` with kind `compliance_returned` and a `reason`
  payload; no migration is needed.
- Matching is rules over page 1 text only: a scanned PDF without a text layer, a note that names its
  provider only in a signature image, or a layout whose labels differ from the ones listed will be
  marked Check and filled in by hand.
