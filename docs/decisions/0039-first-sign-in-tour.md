# 0039 A tour on first sign-in

Date: 2026-11-28

Context: the owner asked that a person's first sign-in, as an admin or any other role, start a tour of
everything that person can open. The app had no onboarding: a new coder or admin met an empty Today
screen and a sidebar of names.

## Choice

- **Steps come from the access rules, not from a list per role.** `components/shared/tour/tourSteps.ts`
  builds the tour from `navFor(user)` (the sidebar's own items, filtered by `canReach`), `canSearch`,
  `canReach(user, "help")` and `canDo`. Each sidebar area is one step titled with its sidebar label; after
  the review queue come the note review steps (Accept or keep for `decide`, Evidence for every note reader,
  Questions for `ask`), and after Security the access log for `manageSecurity`. A role therefore sees
  exactly the areas it can reach, and a new sidebar item joins the tour by itself; a test fails until it
  has a line in `TOUR_TEXT.areas`. Search and Help open and close the practice tour, and the last step
  points at "Take the tour" in the account area.
- **Two tours, one per console.** The tour key is the account's realm (`practice` or `hq`, decision
  [0033](0033-hq-on-its-own-host.md)): practice roles get the practice tour in the practice shell, HQ
  accounts the HQ tour (Overview, Practices, Activity log, Demo requests, Team, Security, and any HQ
  area added to the sidebar later, such as Spend) the first time they open `/hq`.
- **A spotlight built here.** No tour library: a full-screen transparent native `<dialog>` opened with
  `showModal()` holds a cut-out ring (one element whose 200vmax spread shadow is the scrim) and the card.
  The modal makes the page inert, keeps focus in the card (Tab also wraps inside it), suppresses the
  global shortcuts (`useShortcuts` ignores keys while a dialog is open) and gives the card the dialog
  role, named by its title and described by its line. Right and Left move, Enter moves on, Escape skips;
  a polite live region reads each new step with "highlighted" when an element is lit.
- **Targets are marked, not searched for.** Sidebar links carry `data-tour` set to their `href`, sidebar
  actions their icon name (`search`), and the account-area tour button `tour`. These are the only edits
  to the sidebar entries. A step whose target has not appeared within two seconds, or has no room for the
  card beside it, shows the card centred over the dimmed page instead.
- **The card never covers what it describes.** `tourPlacement.cardSpot` tries right, below, above and left
  of the padded target and keeps the first side where the whole card fits inside the viewport with a 16 px
  margin; when none fits it returns nothing and the card is centred without a spotlight. The target is
  scrolled into view and re-measured on resize, on any scroll and when its size changes.
- **Each area's page opens behind its step.** A step names its page; the tour navigates there, so the
  tour visits the app rather than describing it, and returns to the page it started on when it ends. On a
  screen narrower than the sidebar breakpoint the tour opens the menu first and closes it at the end.
- **Shown once per person, on every device.** `person_tours` (`user_id`, `tour`, `version`,
  `completed_at` or `skipped_at`; one row per user, tour and version) stores the outcome.
  `GET /api/account/tours` lists the signed-in user's rows for their realm's tour; `PUT
  /api/account/tours/{tour}` with `{version, outcome}` records one. A tour of the other realm is refused
  (403), and the first outcome recorded for a version is kept: a replay or a second device writes nothing
  new. The client's `TOUR_VERSION` (1) decides when a tour is due, so a large change to the tour raises it
  and every person sees the new tour once. Rows go with their user (`ON DELETE CASCADE`), so deleting a
  practice needs no change to its deletion list; a tour row records nothing about patients or notes.
- **When it does not start.** A billing-only session (a plan that has ended) neither starts the tour
  nor offers it, so the full tour waits until the plan is renewed. If the tour status cannot be read, the
  tour waits for the next visit rather than risk showing it again to someone who has seen it. A failed
  save shows the error in a toast.
- **Replay.** "Take the tour" on the Help page and in the account area of the sidebar (an icon when the
  sidebar is collapsed) opens the tour again; it uses the overlay store, as search and the shortcuts
  dialog do.
- **Motion.** The ring and the card slide between steps with `transform` only, and only under
  `motion-safe`; with reduced motion the target is scrolled into view without smooth scrolling.
  `prefersReducedMotion` moved from the landing page to `lib/media.ts`, which the tour shares.

## Alternatives

- A tour library (Shepherd, Driver.js, react-joyride) would have added a dependency, its own styles and
  its own focus handling for one screen; the owner's rule is no new dependencies.
- Remembering the tour in local storage would show it again on every new device and after clearing the
  browser.
- One row per user with a `seen_version` column would overwrite the earlier outcome when a new version is
  recorded.

## Follows

- Migration 0012 creates `person_tours`.
- An HQ area added to the sidebar needs a line in `TOUR_TEXT.areas`, or the tour test fails.
