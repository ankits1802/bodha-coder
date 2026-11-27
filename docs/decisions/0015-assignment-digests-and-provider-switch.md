# 0015 Who may assign notes, when the daily summary goes out, and how a provider moves between requests

Context: notes gained an assignee, people asked for a morning summary, and providers with several open
requests had to verify once per link.

Choice:

- Assignment. An admin assigns any active note reader of the practice, or nobody. A coder or CDI
  specialist may take a note only when it is unassigned and may release only their own; taking a
  note someone else holds is an admin's call. Compliance, billers and viewers do not assign. Only open
  notes take a change, so an approved or exported note keeps the name of whoever had it, and every
  change is an `assigned` row in the access log.
- Daily summary. Once per practice day, from 07:00 in the practice time zone, idempotent through an
  `activity` row `digest sent` whose detail is the local date, under a per-practice advisory lock.
  The email carries counts and a link only. A practice whose plan ended gets none. A failed email to
  one person is logged and the others still go out; the day is then marked sent, so nobody gets two.
- Provider requests. A provider session stays bound to one request. Switching issues a new provider
  token for another request of the same provider and practice that is `sent` and not expired, with
  the usual session length; the token proves the code was confirmed for this provider.

Follows: the worker calls `send_due_digests(db, messenger, now)` on its five-minute loop. Searching
logs only the result count, never the words typed, because they are often patient names.
