# 0043 One findings list, and returns to the coder that keep their reason

Date: 2026-11-28

Context: the measured workflow baseline found that note review spread a note over six tabs (Codes,
Questions, Suggested wording, Audit risk, Risk adjustment, History), that `y` and `n` worked only in the
open tab, that a coder checked an empty Questions tab on every note, and that approving the last note of a
lane landed on an empty list. Compliance could return a note without a reason; with a Critical audit risk
and no code change the note came back as "Matches the note" in Ready to approve and could be approved with
the rest. A note already asked still offered Ask, and sending failed with "already asked … since:
cdiq-9a7f310833ea5468", an internal id. The provider's day listed every note of the day above the
note's own summary.

## Choice

- **One list ordered by impact.** `reviewList.ts` builds the groups from the note view: what stops
  approval (a choice that departs from Bodha without a reason, a billed code Bodha could not confirm, an
  item compliance returned, a Critical audit risk while compliance holds the note), changes by the size of
  their dollar change, questions, risk adjustment, then audit risks, audit findings and wording. Findings
  that only confirm the bill fold into one supported group. A wording gap sits under the code finding whose
  billed or suggested code it names; the rest are rows. History moved into a drawer with every section it
  had, plus the returns.
- **The dollar change per finding comes from the server.** `services.finding_impacts.amount_change`
  prices the claim with the finding accepted and with it turned down (the other findings at their current
  choices) with the Medicare national estimate of [0014](0014-units-and-medicare-national-estimates.md),
  and the note view sends it as `amount_change` (null when either side cannot be priced). Deriving it in
  the browser from the claim lines would only know prices for codes already on the claim, and the order
  would shift as the coder decided.
- **Filters instead of tabs.** All, Changes, Questions, Risk and Guidance filter the same list. Risk
  holds risk adjustment and audit risks, Guidance the wording, audit findings, checklist and measures. The
  filter is `?filter=`; old links keep working: `tab=codes` opens Changes, `wording` Guidance, `audit` and
  `risk` Risk, and `tab=history` (and the new `history=1`, used by mention emails and the inbox) opens the
  History drawer.
- **Keys work on the whole list.** `j` and `k` (and the arrows while focus is in the list) move the bar
  over the findings with a choice in the order shown, `y` and `n` decide the barred one, Shift+Y records
  acceptance of every supported finding not yet decided in one `PUT /decisions` (a supported finding's
  only choice is keep, which never departs from Bodha, so no reason is asked), and `e` opens the billed
  codes with Enter to save. Next and previous note moved from `j` and `k` to Shift+J and Shift+K, since
  moving within the note is the more frequent step. Decision segments take left and right only
  (`SegmentedControl` `orientation="horizontal"`), so up and down stay with the list. The registry
  learned `withShift` and arrow keys; arrows fire only inside `[data-shortcut-arrows]` or from the page
  itself, so they keep scrolling and moving inside other controls.
- **Returns keep their reason.** Returning needs one of six structured reasons (Level not supported,
  Documentation missing, Coding error, Ask the provider, Payer policy, Other) with an optional note,
  required for Other, through the picker the override reasons use (now `components/shared/reason-picker`,
  keys 1 to 6). `note_returns` keeps each return append-only with the flag it cleared and the finding keys
  to decide again; `note_changes` keeps the cleared flag with the reason as text; the inbox tells one
  person with `{reason}` only.
- **A returned note is the coder's until a fresh decision.** Placement puts it in the coder lane with
  reason `returned` and headline Returned after compliance and waiting on the provider and before
  everything else, so it is never "Matches the note"; auto-approval needs `matches` and never takes it.
  Bulk approve refuses it, and approval refuses it until every returned item still on the note has a
  decision recorded after the return. The returned items are every change-kind finding with a choice to
  make, risk adjustment aside: compliance names a reason, not the codes, and a return asks the coder to look
  at the claim again. The recipient is whoever flagged the note, else its assignee, else the last person who
  decided a finding on it; a note placed in compliance automatically was never approved, so "the coder who
  approved" is read as the last coder to decide.
- **Moving on.** When a lane empties after approval, `nextLane.ts` reads the lane counts of a fresh
  Today summary (three rows rather than a page of fifty) and opens the queue on the next lane view with
  work the role can do (approve, coder,
  questions to send, compliance; waiting on provider is never offered); a note opened from a split of the
  provider lane carries `reason` with `lane`, so next and previous stay inside it. A compliance decision
  made inside a note returns to `/compliance`.
- **Ask and the repeat refusal.** Ask provider is offered only for open questions no sent request already
  covers. The 409 for a repeat reads "These questions were already sent on 27 Nov 2026; remind the
  provider instead", the day of the latest blocking request in the practice's time zone, and names no key.
- **Same day.** The note's summary comes before the provider's day, and the other notes of the day fold
  behind "2 other notes that day".

## Alternatives

- Letting compliance tick the findings to decide again would be more precise but adds a second control to
  a one-reason dialog; the reason plus every change finding is simpler and errs on the side of a fresh look.
- A `returned` flag on the note without its own table would have kept the reason only as text in
  `note_changes`; the structured reason and the item keys need a row of their own to stay queryable and
  unchanged.
- Keeping `j` and `k` for notes and arrows alone for findings would have left the list without letter keys
  on laptops where the arrows are far from `y` and `n`.

## Follows

- Migration 0018 adds `returned` to the lane reasons, `notes.returned_at`, and `note_returns` under the
  append-only, stamp and truncate guards of [0038](0038-seven-year-retention-and-tamper-evidence.md);
  the runtime role gets SELECT and INSERT on it and UPDATE on `notes.returned_at`, and
  `bodha_purge_practice` removes the practice's returns before its note changes.
- Keystroke counts for the coder flow (three notes, one billed-code edit) were counted from the key paths
  rather than measured again; they are in the change description.
