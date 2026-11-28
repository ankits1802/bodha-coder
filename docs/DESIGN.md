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

## Navigation

The sidebar holds one entry per area a role works in ([0041](decisions/0041-streamlined-navigation-and-first-day.md)).
Pages that belong together are tabs of one entry, not entries of their own.

| Rule | How |
|---|---|
| Entries | Admin: Today, Inbox, Upload notes, Review queue, Compliance, Billing, Insights, Settings. Compliance: Today, Inbox, Review queue, Compliance, Insights. Coder: Today, Inbox, Upload notes, Review queue. CDI: Today, Inbox, Review queue. Biller: Today, Inbox, Billing. Viewer: Today, Insights. The practice switcher, search and Help are not entries |
| Area tabs | Billing (Ready to bill, Remittances), Insights (Overview, Quality, Access log) and Settings (Setup, Team, Plan, Security) show a tab row above the page, drawn like a segmented control (`components/ui/Tabs`). Each tab is its own address; arrow keys, Home and End move focus and Enter or Space opens a tab, so arrowing never loads a page. A role sees only the tabs it may open, the entry opens the first of them, and an area with one tab shows no row |
| Account menu | The person's name and role at the foot of the sidebar (the avatar when collapsed) opens a menu: Account (signed-in devices, recovery codes, the daily email and the practices), each practice with the role and the current one checked (choosing one switches), Leave for each practice (confirmed in a dialog), New practice, Take the tour and Sign out. A billing-only session offers Sign out only |
| Today | The one primary button follows the role: Start reviewing (a coder's own next note, else an unassigned one, else My work), Send questions (the Questions to send view), Review compliance, Start billing; an admin gets Start reviewing once the practice has notes. Open blind coding assigned to the person is listed under Assigned to you, with a link to Training |
| First steps | Until every step is done, an admin's Today starts with Get set up: providers (Import CSV, Add provider), payers (Add payer), the checks as switches with Save checks, Invite people (one form with a row per person), Use recommended (two-step for every role, sign-out after 7 days without use, the access log kept 7 years) and Choose a plan. Each step's name links to its place in Settings and carries the setup marker; the next open step holds the primary button while the practice has no notes. Hide appears once providers are in |
| Single sign-on | One panel, the same for a practice (Settings → Security, admins) and an organization (its Single sign-on tab): Bodha's Entity ID and Reply URL as selectable code with Download metadata; the identity provider from a metadata file or URL with its certificates, each with its expiry and Remove; the verified domains, the break-glass admins and the switches as switch rows; Save, Turn off (confirmed) and Test sign-in, whose result lists what arrived. On the sign-in page an email whose domain requires single sign-on hides the password field and turns Continue into Continue with single sign-on, with Use a password below for break-glass admins; an optional domain adds a second Continue with single sign-on button |
| Forms | A field's optional marker is read after a pause ("NPI, optional"). The provider dialog shows name, credential, NPI, usual place, usual payer (while the practice lists payers) and email; specialty, questions by text, active and credentialing sit behind More, which opens by itself when one of its fields needs fixing |

## Upload notes

Files chosen or dropped anywhere land on the upload screen ([0059](decisions/0059-payer-known-when-the-note-is-read.md)).

| Rule | How |
|---|---|
| All files | One panel: Provider for all, Date of service for all, Place of service for all, Payer for all with its Recommended marker (read after a pause, like optional), and Visit type. A field whose files differ shows Several |
| Payer | Shown only while the practice lists active payers. Each file row has a Payer list after Place: None, then the payers; a payer page 1 names without enough confidence sits first under Suggested, the rest under All payers. A payer page 1 names clearly, else the provider's usual payer, fills the row as the usual place does. A missing payer never blocks Start reading and never marks a row to check |
| Read again | In note review, a ready note whose payer changed in a way that alters the read shows Read again with this payer (secondary) beside the payer list; it never reads again by itself |

## Feedback and flow

A reversible action (approve, approve all) happens at once and offers Undo in a toast at the bottom
for eight seconds; a confirmation dialog is kept for destructive actions only (void, close or purge, replace a PDF,
block). Loads that fill a screen show a skeleton of its layout; small panels keep the spinner. In
note review the finding that `y` and `n` act on carries a dark bar at its left edge, and focus moves
to the next finding after each decision, then to Approve. Form fields are checked when they lose
focus, not only on submit.

## Figures

A figure on a dashboard opens the records it counts ([0058](decisions/0058-figures-open-their-records.md)).

| Rule | How |
|---|---|
| Link | `StatCell` with an `href`: the whole cell is the link, named by every word it shows with pauses ("Organizations, 3"; "Waiting, 12, 3 reading now"); the row-hover background on hover and an inset focus ring. The figure keeps the label colour: no purple, underline or chevron. Today's lanes are the same cells, larger, with the lane's dot |
| Destination | A list that already exists, with its filter in the address, counted by the same query: HQ Organizations to `/hq/organizations`, Practices to `/hq/practices?status=live` (Live is active or trial), Model cost this month to `/hq/spend` for the month so far; each Today lane to its queue lane (Compliance to `/compliance` for those who can open it); Ready to bill to `/billing`, Exported today to `/billing?show=today` |
| Plain | Rates, medians, money estimates, figures over a rolling window, an Insights period or a whole organization, totals of the table right below, and any figure whose list the viewer's role cannot open stay text; so does every figure in a billing-only session |

## Note review

One findings list replaces the review tabs ([0043](decisions/0043-one-findings-list-and-returns.md)).

| Rule | How |
|---|---|
| Order | Before you approve (a missing override reason, a billed code Bodha could not confirm, an item compliance returned, a Critical audit risk while compliance holds the note), Changes from the largest estimated dollar change down (the change shown after the status), Questions with Ask and the requests sent, Risk adjustment (scores, categories, suspected conditions), then Audit and wording (audit risks by severity, wording that belongs to no finding, audit findings, the checklist and quality measures). Each group has a small secondary heading |
| Supported | Findings that only confirm the bill fold into one "12 supported" text button; Accept all supported (secondary, with its key) records them in one save and becomes an Accepted dot |
| Wording | Suggested wording sits under the finding whose code it rewords: the note's words, the recommendation and the wording in a muted figure |
| Filters | A small segmented control above the list: All, Changes, Questions, Risk, Guidance, each with its count. The choice lives in `?filter=`; old `?tab=` links open on the nearest filter (codes to Changes, wording to Guidance, audit and risk to Risk) |
| History | History (plain) at the end of the filter row opens a drawer from the right, full height, at most 37.5 rem wide and the full width on a phone, with Close (plain); Escape closes it. `?history=1` and the old `?tab=history` open it |
| Returned | A note compliance returned shows a warn alert, "Returned by Jordan Diaz: Level not supported · …"; each item to decide again is listed first with a Decide again dot and no choice selected until it is decided |
| Keyboard | `j` and `k` or the down and up arrows move the bar between findings with a choice (the arrows only while focus is in the list or on the page; decision segments move with left and right), and past the last one to Approve; `y` and `n` decide the barred finding wherever it sits; Shift+Y accepts all supported; `e` edits the billed codes and Enter saves, moving to the reasons first when none is chosen (a digit picks one, Enter saves); Shift+J and Shift+K open the next and previous note; `a` and `q` are unchanged |
| Return to coder | A dialog with the six reasons as radios numbered 1 to 6 (Level not supported, Documentation missing, Coding error, Ask the provider, Payer policy, Other), Note (optional, required for Other) and Return to coder as the primary. The compliance list and the note open the same dialog |
| After the work | Approving the last note of a lane opens the queue on the next lane with work the person can do; a compliance decision made inside a note goes back to Compliance. Ask provider is hidden while a sent request covers the open questions |
| Same day | The provider's day sits below the summary: its line of facts first and "2 other notes that day" as a text button that unfolds the list |

Text meets WCAG 2.2 AA contrast (4.5:1) on every surface, including the sidebar. Apple's lighter
tertiary grey (#86868B) reaches only 3.2:1 on the sidebar, so it is used for decoration such as focus
rings, never for text. Key hints on grey fills use the soft label colour. Every control is at least
24 px in both directions or spaced so (WCAG 2.5.8), and a control's accessible name contains its
visible words: avatar initials are drawn from `data-initials` by CSS, so they are not part of the text
a speech user reads out. The browser journeys run axe on every page they open and fail on serious or
critical violations ([0050](decisions/0050-browser-journeys-and-production-canary.md)).

## Claims to the clearinghouse

Shown only once the practice has a clearinghouse ([0051](decisions/0051-clearinghouse-837p.md)); without
one, Ready to bill looks as before.

| Rule | How |
|---|---|
| Actions | SFTP: Send N claims is the one primary, Download 837P and Export claim lines are secondary. Portal upload: Download 837P is the primary. Both act on the page's rows that are ready, or rejected or not delivered with nothing missing |
| Claim column | A dot and a word: Missing information (warn), Ready, Sending, Sent, Accepted (ok), Rejected and Not delivered (bad), with the first reason or up to three missing items as one secondary line ("Charge for 99214, Payer ID and 2 more"). Details (plain) opens the claim details |
| Claim details | A dialog: the name as read on the note as its subtitle, patient fields, relationship (Self, Spouse, Child, Other) with the subscriber's name only when not Self, member ID and group number, a payer select only while the payer is missing, what is still missing above the form, Save (primary) |
| Claim files | A panel under the table: each file's name, claims, total, delivery and acknowledgment counts with Download (secondary), and Upload response (secondary) |
| Setup | Clearinghouse: identity fields, Test or Production as a segmented control, Portal upload or SFTP; for SFTP the host, user name, password or private key (empty after saving, "Saved" as its placeholder) and folders, Read host key (secondary) showing the fingerprint to accept, Save (primary), Test connection (secondary), Remove (danger, confirmed). Payments: a charges table with Add charge and Import CSV |

## Signatures

| Rule | How |
|---|---|
| Capture | A segmented control (Draw, Type, Upload), the Full name field, then a 5:2 white frame: the pad, the typed name, or the photo. Undo and Clear are plain buttons under the pad. Continue (primary) checks the image; the preview then offers Redo (plain) and Adopt signature (primary). No helper sentence |
| Type | The one place another face appears: the typed name is drawn in the system script font (`--font-signature`), because it stands for handwriting. Every label around it stays in the system font |
| Keyboard | The segmented control is the first stop; arrows reach Type, so a person can sign with the keyboard alone |
| First approval | Approving without an adopted signature opens Add your signature in a dialog; adopting it finishes the approval with no other click. Later approvals look exactly as before |
| Security page | A Signature panel shows the adopted signature with Replace (secondary), which opens the same dialog |
| Secure link | The provider's signature sits in the addendum or level panel above the confirmation box, with Remember my signature for this practice; Sign and add to note or Send stays the only primary |
| Verify page | `/verify`: the large title, a code field with Verify (primary), then a panel with Seal verified or Seal does not match as a dot and a word, what no longer matches, the facts as a list, and Check a PDF (secondary), answered with a dot and a word |

## Tour

The first sign-in to each console opens a guided tour of every area the person's role can reach
([0039](decisions/0039-first-sign-in-tour.md)).

| Rule | How |
|---|---|
| Spotlight | The page dims with the scrim colour except a ring around the real element (its sidebar entry, the search action or the account menu on the person's name), padded 6 px with the field radius and a white 2 px outline. Each area's page opens behind its step |
| Card | White panel, 20 rem wide or the screen less 2 rem: "3 of 12", a headline title, one line of at most twelve words, Skip tour (plain) at the left and Back (secondary) and Next or Done (primary, the only purple) at the right. No helper copy beyond the line |
| Placement | Right of the target, else below, above or left, wherever the whole card fits with 16 px to spare; it never covers the target. With no room, or when a step has no element (welcome, note review), the card is centred over the dimmed page |
| Keyboard | Focus starts on Next and stays in the card; Right and Left move, Enter moves on, Escape skips. Each new step is read out with "highlighted" when an element is lit |
| Small screens | Below the sidebar breakpoint the menu opens first and the card sits below or above the entry |
| Motion | The ring and card slide with `transform` only under `motion-safe`; reduced motion jumps and scrolls without smoothing |
| Replay | "Take the tour" on Help and in the account menu |

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
| Plan cards | `PlanCard` is shared by `/settings/plan` and `/pricing`: name, price in whole dollars with its unit (per provider / month or / year, Free for the trial length, Custom), and the limits as a list. The Monthly / Annual segmented control names the months a year saves inside the Annual segment |
| Choosing | On `/settings/plan` the two plans bought online are native radios drawn as cards (the whole card is the label; checked and focus rings from `OPTION_CARD`); one primary "Choose plan" acts on the choice and opens "Pay with" (Card via Stripe, PayPal) only when both are set up. A subscriber sees "Manage billing" instead (primary for Stripe; secondary beside a danger "Cancel at period end" for PayPal, which confirms first). Enterprise is a secondary "Contact sales" |
| Status | The plan's standing is a dot and a word (Trial, Active, Payment due, Ending, Canceled); usage reads `3 of 5` |
| Banner | Admins see one inline alert at the top of the content for a trial's last days or a failed payment, with a link to `/plan` and "Hide until tomorrow"; it is not shown on `/plan` |
| Pricing page | `/pricing` uses the landing nav (section links point back to `/`) and the landing type scale; "Start free trial" is primary on the trial card only, secondary on the paid cards, and Enterprise opens the demo request. Plan names and monthly prices arrive in the server's HTML with Product and Offer structured data for the two paid plans; when the server cannot reach the API, the cards load in the browser as before |

