# 0024 Fewer steps and less waiting for the people who work notes all day

Context: with the demo model ([0023](0023-demo-model-backend.md)) every lane could be worked end to end,
and six flows were measured with Playwright at 80 ms of added latency: coder review, bulk approve,
provider query, biller export, admin first run and the compliance lane. The flows already took few
clicks; the cost was in waiting (every note fetched the whole lane, the places and the payers again and
waited for its own detail), in keyboard gaps (no way to decide a finding without the pointer), in a
start button that went to the queue when pressed before Today had loaded, and in the provider page,
which put the note above the question on a phone.

## Choice

- A small in-memory cache under `useRemote` (`hooks/remoteCache.ts`): lookups are kept five minutes,
  the lane order two minutes, and the next note is prefetched while the current one is open. A request
  already running for a key is shared. It is emptied when the session ends and never touches browser
  storage. A prefetch is a normal read and is written to the access log as `opened note`: the record
  states what reached the browser, which is what a disclosure log is for.
- Keyboard: `y` and `n` accept or reject the selected finding (the suggestion's own choice, or keep or
  skip), focus moves to the next finding and then to Approve, `q` asks the provider (`p` still works),
  `n` starts reviewing on Today, and `u` runs the Undo of the last toast. Shortcut listeners attach
  before the first paint so a key pressed the moment a prefetched note appears is not lost.
- Decisions show at once and are saved in order; Approve waits for them. A failed save restores the
  last saved state with the error.
- Undo instead of confirmations for reversible actions: approving a note or every matching note shows
  a toast with Undo, backed by `POST /api/notes/reopen` (all or none, `reopened` logged per note).
  Destructive actions keep their confirmation.
- Approve all in the Ready to approve lane is one button. Billers start on Ready to bill and compliance
  on Compliance. The queue lane, assignee and provider filters and the compliance segment are
  remembered per user; billing's segment is not, because its default (not exported) is the day's work.
- Compliance hides a decided case at once and has the next one loaded. Setup moves to the next
  incomplete section after a save; NPI and EIN fields, provider and invite fields are checked when they
  lose focus. Note review shows a skeleton while a note loads.
- The provider page lists the questions first on a phone, with 48-pixel answer rows, and verifies the
  six-digit code as soon as it is complete.
- Two defects the measurements surfaced are fixed: a compliance "keep" reason over 23 characters
  overflowed `code_sets.reason` (40) and failed with 500; the reason now goes to the access log and the
  request limits it to the access-log detail length (300). The ask dialog listed "Other" twice.

## Alternatives

- A data-fetching library (SWR, TanStack Query) would bring caching and deduplication, but the app has
  one client and one hook; sixty lines of cache cover what the measurements asked for without a new
  dependency.
- Optimistic approval (navigate first, approve in the background) would save one round trip more, but
  an approval refused by the server (held claim, unconfirmed code) would surface after the coder had
  moved on; the next note is prefetched instead, so the wait after Approve is the approval itself.
- Prefetching the PDF was left out: its signed link expires after `PDF_LINK_SECONDS` (60) and a new
  link is signed on every open, so the browser could not reuse it.

## Follows

- Measurements and the scripts that produced them live outside the repository; the before and after
  figures are in the change description.
