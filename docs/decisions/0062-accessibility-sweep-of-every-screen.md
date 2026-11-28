# 0062 A WCAG 2.2 AA sweep of every screen in CI

Date: 2026-11-28

Context: the browser journeys ([0050](0050-browser-journeys-and-production-canary.md)) run axe on the pages
a role's day passes through, which leaves most screens, roles, empty states, dialogs, the phone layout and
reduced motion unchecked, and axe alone does not test keyboard reach, focus indicators or what a dialog
does with focus.

## Choice

- **Where.** `frontend/e2e/sweep`, two Playwright projects beside the journeys in `playwright.config.ts`:
  `sweep-setup` seeds once (`world.setup.ts`, `python -m tests.e2e_seed sweep-day`) and writes the result
  to the runner's temporary folder; `sweep` depends on it, so every visit reads one shared world and the
  journeys keep seeding their own. The `e2e` job runs both with the journeys; a failure fails CI.
- **The world** (`backend/tests/e2e_seed/sweep.py`): a practice with every role (admin, coder, CDI,
  compliance, biller, viewer), a provider, a payer and seven notes read by the worker into every lane,
  two of them approved, a blind audit sample and a training set for the coder, one question sent to the
  provider and an organization over it; a practice with only its admin; a practice whose plan ended
  yesterday (the billing-only session); an HQ person; a pending invitation; a demo request. The plan's
  end is written to the database, because renewal refuses a past date and the sweep cannot wait a day.
- **Sessions.** Signing in is rate limited per address and a two-step code works once per step, so the
  sweep does not sign in. Each worker opens one session per person with `services.auth.start_session`
  (`python -m tests.e2e_seed.sessions`, which refuses production like the seed) and hands the refresh
  cookie from test to test, since every refresh rotates it. A failed test drops the person's session and
  the next test opens a new one. Each session writes a `signed_in` auth event named for the sweep.
- **What is visited.** Every route of the sidebar and its tabs, for every role the app's own rules
  (`canUse` in `lib/roles.ts`) let open it, on the busy practice, and for the admin also on the empty
  practice; every setup section; the note review in each lane for the roles that work it; the blind audit
  and training screens; the organization area; the billing-only plan and its redirect; every HQ page,
  practice tab and organization tab on the HQ host; the public pages (landing, pricing, legal, sign-in on
  both hosts, sign-up, join, practice completion, forgot and set password, verify with and without a
  code, domain verification, the provider's link before and after the code, a missing page); the main
  dialogs; a phone width (390 by 844) for key screens; reduced motion.
- **What each visit checks.** The page settles (its heading, no spinner, skeleton or `aria-busy`, and
  its entrance animations ended, for at most eight seconds, since a fade-in is not a contrast defect), stays
  on the route asked for, is not the "role can't open this page" state, and no request failed on the
  server. Then axe with the WCAG 2.0 to 2.2 A and AA tags, failing on serious or critical violations
  (`support/accessibility.ts`); `target-size` covers 24 by 24 pixel targets. Then Tab from the top of the
  page must reach the primary action, found as the one control styled `bg-primary` (the design allows
  purple only there), and the focused control must look different from its resting state.
- **Dialogs** are opened from their trigger by keyboard (focus, Enter), checked by axe, then Tab and
  Shift+Tab past every focusable element must leave focus inside the dialog, and Escape must close it
  and return focus to the trigger (`support/keyboard.ts`).
- **Phone and motion.** At phone width the page must not scroll sideways (reflow). With reduced motion
  asked for, no animation may loop forever.
- **Focus return lives in the dialog primitive.** `useModalDialog` remembers what had focus when a
  dialog opened and gives focus back when the dialog closes or its parent removes it, if focus would
  otherwise be lost. Many dialogs are mounted only while open, and removing an open `<dialog>` drops focus
  to the body, which the browser does not repair.
- **A pending button keeps focus.** `Button` marks a pending action `aria-disabled` and `aria-busy` and
  refuses clicks, Enter and form submission while it waits, instead of setting `disabled`: a disabled
  button drops focus to the body, so approving without a signature lost focus behind the signature dialog
  and could not get it back. `disabled` stays for actions that are not allowed.
- **A table that scrolls sideways is a keyboard stop.** `Table` measures its scroller; when the table is
  wider than its column, the scroller becomes a region named like the table with `tabIndex=0`, so it can be
  scrolled from the keyboard, and it stays out of the tab order when the table fits. The scroller is
  positioned, so visually hidden header text cannot widen the page past it.

## Alternatives

- **Signing in once per role and sharing the storage state**: the first refresh rotates the cookie and
  ends the session for every other worker.
- **Seeding per test**: minutes of uploads and worker reads repeated for pages that only read.
- **A list of primary actions per page**: duplicates the screens' strings and drifts; the design already
  marks the primary action with one style.
- **Turning rules off or lowering the impact threshold**: hides the defects the sweep exists to find.

## Follows

- `README.md` (Checks) and `docs/ARCHITECTURE.md` (Browser journeys) describe the sweep; `docs/DESIGN.md`
  (Feedback and flow) says how pending buttons and dialogs treat focus.
- The `frontend-practices` skill no longer says to disable submission while a request is pending: it says
  to refuse a second submission without moving focus off the control, for the reason above.
