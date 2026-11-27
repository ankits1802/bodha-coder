# Design system

The approved screens are the Bodha Assure design canvas. These rules bind every screen.

## Type

One family: the Apple system font (`-apple-system, BlinkMacSystemFont, "SF Pro Text"` and
`"SF Pro Display"` for titles), with Inter where SF is unavailable. No serif, no italic display
face, no separate code font: codes use the same family with tabular figures.

| Role | Size and weight |
|---|---|
| Large title | 34, bold, tracking -0.025em |
| Title | 20 to 24, semibold |
| Headline | 15 to 17, semibold |
| Body | 14, regular |
| Secondary | 12.5 to 13, regular, secondary label colour |

## Colour

| Token | Value | Use |
|---|---|---|
| page | #FAFAF8 | page background |
| surface | #FFFFFF | panels |
| sidebar | #F2F2F4 | navigation |
| separator | #E5E5EA | lines |
| label | #1D1D1F | text |
| secondary | #6E6E73 | secondary text |
| tertiary | #6E6E73 | the smallest labels; same colour as secondary so it passes 4.5:1 on the sidebar, set apart by size |
| action | #3A2470 (hover #2D1B59) | the primary action button only |
| ok | #34C759 | supported, matches |
| warn | #FF9F0A | needs detail |
| bad | #FF3B30 | not supported, billed too high |
| low | #0A84FF | billed too low |

Status is a small dot beside a word, never colour alone. Dark purple appears on the primary
action button and nowhere else.

## Shape and controls

Grouped panels with 14px radius, pill buttons (primary, secondary, plain, danger), segmented
controls, macOS-style sidebar with small line icons, toggles in system green. One primary action
per screen. No helper sentences: labels, layout and state carry the meaning.

## Controls

The app draws its own lists and calendars; no native select or date input appears anywhere. Neither
control uses the action colour.

| Control | Behaviour |
|---|---|
| Select | A field-shaped button with the chosen label and a chevron. It opens a floating list below the field, or above it when there is no room, at most 320 px tall and scrolling, never clipped by a dialog or a table. The chosen option carries a check mark and status options carry their dot. Arrow keys, Home, End and Page keys move; typing jumps to the first matching label; Enter or Space chooses; Escape closes and returns focus; Tab chooses and moves on, like a native select; a click outside closes. Lists of more than twelve options open with a search box that filters by label and says No matches. Forms use the full field, filter bars the compact pill, table rows the borderless inline form. |
| Practice switcher | At the top of the sidebar, only for a person in two or more practices: the current practice's name with a downward chevron (its initials in a small tile when the sidebar is collapsed) opens a menu of the practice names with the current one checked. Focus starts on the current practice; arrow keys move, Enter chooses, Escape or Tab closes and returns focus. Choosing another practice reloads the app on that practice's home. |
| Date picker | A text field showing the day as the app writes it (27 Nov 2026) with a calendar button. Typed days are read day first (27/11/2026), as ISO or in the written form; a day that cannot be read or lies outside the allowed range turns the field red when it loses focus and is not passed on. The calendar starts weeks on Monday, rings today, fills the chosen day in dark, disables days outside the range, and offers month and year lists and Today. Arrows move by day and week, Page Up and Page Down by month (with Shift by year), Home and End to the ends of the week, Enter picks, Escape closes; focus returns to the calendar button. A date range keeps its end on or after its start. |

## Feedback and flow

A reversible action (approve, approve all) happens at once and offers Undo in a toast at the bottom
for eight seconds; a confirmation dialog is kept for destructive actions only (delete, replace a PDF,
block). Loads that fill a screen show a skeleton of its layout; small panels keep the spinner. In
note review the finding that `y` and `n` act on carries a dark bar at its left edge, and focus moves
to the next finding after each decision, then to Approve. Form fields are checked when they lose
focus, not only on submit.

Text meets WCAG 2.2 AA contrast (4.5:1) on every surface, including the sidebar. Apple's lighter
tertiary grey (#86868B) reaches only 3.2:1 on the sidebar, so it is used for decoration such as focus
rings, never for text.

## Tour

The first sign-in to each console opens a guided tour of every area the person's role can reach
([0039](decisions/0039-first-sign-in-tour.md)).

| Rule | How |
|---|---|
| Spotlight | The page dims with the scrim colour except a ring around the real element (its sidebar entry, the search action or the account area's "Take the tour"), padded 6 px with the field radius and a white 2 px outline. Each area's page opens behind its step |
| Card | White panel, 20 rem wide or the screen less 2 rem: "3 of 12", a headline title, one line of at most twelve words, Skip tour (plain) at the left and Back (secondary) and Next or Done (primary, the only purple) at the right. No helper copy beyond the line |
| Placement | Right of the target, else below, above or left, wherever the whole card fits with 16 px to spare; it never covers the target. With no room, or when a step has no element (welcome, note review), the card is centred over the dimmed page |
| Keyboard | Focus starts on Next and stays in the card; Right and Left move, Enter moves on, Escape skips. Each new step is read out with "highlighted" when an element is lit |
| Small screens | Below the sidebar breakpoint the menu opens first and the card sits below or above the entry |
| Motion | The ring and card slide with `transform` only under `motion-safe`; reduced motion jumps and scrolls without smoothing |
| Replay | "Take the tour" on Help and in the account area (a compass icon in the collapsed sidebar) |

## Motion and haptics

Motion explains what Bodha does: a reading beam, evidence inked like a marker, a struck code replaced by
the supported one, pages that land, wires that connect a sentence to its code. It never decorates a
control. Rules:

| Rule | How |
|---|---|
| Cheap to draw | only `transform`, `opacity`, `background-size` and `stroke-dashoffset` animate; no animation libraries |
| Scroll without React | `ScrollStage` writes one `--p` (0 to 1) per section in a `requestAnimationFrame`; CSS derives every act from it. Modes: `enter` (the section rises into view), `pin` (a tall track scrolls past a sticky stage), `through` (a line at 85% of the viewport passes through the element, over at least 60% of the viewport: progress lines such as the workflow timeline) |
| Paused off screen | `MotionRoot` marks `[data-live]` elements with `data-onscreen`; infinite animations pause when false |
| Reveals | elements with `data-reveal` below the fold wait (`data-state="waiting"`) and ease in once seen; without JavaScript everything is visible |
| Reduced motion | `prefers-reduced-motion: reduce` shows every final state, unpins the story and lays its acts out as rows |
| Pointer | parallax and the magnetic button follow fine pointers only |
| Haptics | `lib/haptics.ts`: `tap` (primary press), `select` (switch, in-page jump), `success` (approve). The Vibration API where it exists (Android); on touch devices without it, a hidden native switch is ticked, which iOS 18 answers with a system haptic. Only from a user gesture, never on scroll |

## Landing page

The public page at `/` (`features/landing`) follows the rules above with these additions.

| Rule | How |
|---|---|
| One primary | "Start free trial" is the only purple button in each region; "Request a demo" is secondary, and footer actions are text links |
| Product pictures | Mini screens are built from the app's own pieces (`CodeChip`, `CodeChange`, `StatusDot`) and plain shapes, hidden from assistive technology; every word in them still meets 4.5:1, since audits read hidden text too |
| Animating text | Text inside a looping picture moves by transform only; opacity loops are kept to shapes, so text is never caught half transparent |
| One dark band | The workflow timeline sits on the label colour (#1D1D1F) with secondary text in #AEAEB2 (7.6:1); status colours keep their meaning there |
| Truthful figures | A figure is structural ("every suggested code checked against the official code set", "one in ten held") or computed from the visitor's inputs, as in the estimator, which shows its arithmetic and "Your numbers, not ours."; no customer counts, logos, testimonials, certifications or outcome statistics |
| Controls | Role tabs follow the WAI-ARIA tabs pattern (arrows, Home, End, one tab in the tab order); questions are buttons with `aria-expanded` inside level 3 headings; the estimator pairs each range with a labelled number field and names the allowed range beside an invalid value |
| Sample note | "Try it on a sample note." follows the story: three synthetic notes labelled Sample note (billed too high, billed too low with a missed add-on, HCC capture) as tabs, each reviewed by static data in the page, with no request and no model run. The billed codes sit above the findings and the claim below them, updating as each change is accepted, with Ready to approve once all are decided. The current finding carries the dark bar and its evidence is inked in the note, read to screen readers between "Evidence:" and "End of evidence"; after the last decision the note shows the evidence of every accepted change. Accept and Reject are toggle buttons; while focus is inside the review, `y` and `n` (the note review shortcuts) decide the finding that holds focus, else the current one, and focus moves to the next open finding. Start free trial closes the section |
| Pricing teaser | Before the questions: the trial and every plan priced per provider at its monthly price, worded by `cardPrice` from the plan catalog, "No card needed" on the trial, and See all plans to `/pricing`. The server renders the catalog it loaded; without one, the browser fetches it, as on `/pricing` |
| Phones | Section links collapse behind a Sections button below 1024px; the brand, Sign in and Start free stay in the bar |

## Plans and pricing

| Rule | How |
|---|---|
| Plan cards | `PlanCard` is shared by `/plan` and `/pricing`: name, price in whole dollars with its unit (per provider / month or / year, Free for the trial length, Custom), and the limits as a list. The Monthly / Annual segmented control names the months a year saves inside the Annual segment |
| Choosing | On `/plan` the two plans bought online are native radios drawn as cards (the whole card is the label; checked and focus rings from `OPTION_CARD`); one primary "Choose plan" acts on the choice and opens "Pay with" (Card via Stripe, PayPal) only when both are set up. A subscriber sees "Manage billing" instead (primary for Stripe; secondary beside a danger "Cancel at period end" for PayPal, which confirms first). Enterprise is a secondary "Contact sales" |
| Status | The plan's standing is a dot and a word (Trial, Active, Payment due, Ending, Canceled); usage reads `3 of 5` |
| Banner | Admins see one inline alert at the top of the content for a trial's last days or a failed payment, with a link to `/plan` and "Hide until tomorrow"; it is not shown on `/plan` |
| Pricing page | `/pricing` uses the landing nav (section links point back to `/`) and the landing type scale; "Start free trial" is primary on the trial card only, secondary on the paid cards, and Enterprise opens the demo request. Plan names and monthly prices arrive in the server's HTML with Product and Offer structured data for the two paid plans; when the server cannot reach the API, the cards load in the browser as before |

