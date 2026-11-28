# 0041 Fewer sidebar entries and a guided first day

Date: 2026-11-28

Context: a measured walk through every role on synthetic data found 13 sidebar entries for an admin,
7 for compliance, 6 for billers, 5 for coders and 4 for CDI, with pages that belong together (ready to
bill and remittances, insights and quality, setup, team, plan and security) as separate entries and
personal security mixed with the practice's. A new admin needed 34 clicks, 217 keys and 7 sidebar trips
to set a practice up, met a Start reviewing button that opened an empty queue, was asked to sign in
again after choosing a password, and could lose their place on Insurance payers: saving its text fields
jumped to Payments before a payer could be added. The provider dialog showed 16 fields, screen readers
read "NPIoptional", the raw storage path of automatic intake was shown to admins, Checks and Automatic
intake were repeated under every setup section, and HQ said a trial ended in 13 days while the
practice's banner said 14.

## Choice

- **One entry per area, with tabs.** `navItems.ts` stays the one list of sidebar entries; an entry can
  carry `tabs`, each with its own area, and `navFor` keeps only the tabs the role can reach and points
  the entry at the first. Billing has Ready to bill and Remittances (`/billing`, `/billing/remittances`),
  Insights has Overview, Quality and Access log (`/insights`, `/insights/quality`,
  `/insights/access-log`), and Settings has Setup, Team, Plan and Security (`/settings/...`). `AreaTabs`
  draws the row in each area's layout with the Tabs that note review used, moved to `components/ui`;
  page tabs use manual activation so arrowing through them never loads a page. `PLAN_PATH` is
  `/settings/plan` (the checkout and billing portal return there too). With the inbox entry of
  [0042](0042-inbox-upload-matching-queue-views-hq-page.md) after Today, the sidebar has admin 8,
  compliance 5, coder 4, CDI 3, biller 3 and viewer 2 entries (13, 7, 5, 4, 6 and 3 before).
- **Old addresses keep working.** `lib/routeRedirects.ts`, read by `next.config.ts`, sends `/setup`,
  `/team`, `/plan`, `/remittances`, `/quality` and `/quality/review/:id` to their new places with the
  query string, so `/setup?section=payers` and Stripe's return to `/plan?checkout=done` still land.
  `/security` needs the role, so it is a page that sends admins to Settings, Security, compliance to the
  access log (with the old query) and everyone else to their account.
- **The access log is an Insights tab, not part of Settings, Security.** Audit hardening opened the
  access log to compliance as well as admins. Putting it under Settings would have given compliance a
  Settings entry holding one page; under Insights both roles reach it from an entry they already have,
  and Settings, Security holds only the practice's security settings. A team member's Activity
  (Team, More, Activity) opens it filtered to that person for the last 30 days of the practice calendar.
- **An account menu on the person's name.** It holds Account (signed-in devices, recovery codes, the
  daily email, the practices and, once the signature work lands, the signature), the person's
  practices with their role (choosing one switches, as the switcher at the top of the sidebar does),
  Leave for each practice through the same confirmation as the account page, New practice, Take the
  tour and Sign out. The personal page moved from `/security` to `/account`; `SecurityScreen` stays the
  component that page renders, so panels added to it appear there. Search keeps its sidebar action and
  Help its foot entry.
- **Billers lose Review queue and Training from the sidebar** but can still open notes; Training
  leaves every sidebar. Open blind coding assigned to the person is listed on Today under Assigned to
  you with a link to Training, and Assign training is now the Training view of Insights, Quality
  (admins). The inbox entry, with its unread count, sits in the work group after Today; the lane counts are
  fetched only when an entry shows one.
- **Today's main button follows the role**: a coder's own next note, else an unassigned one, else the
  My work view; CDI the Questions to send view; compliance its list; billers Ready to bill; an admin
  Start reviewing only once the practice has notes. Only the note that button opens is
  prefetched, so roles that do not code no longer write `opened note` for a note they never open.
- **First steps for an admin.** Until every step is done or hidden, Today starts with six steps, each
  linking to its place in Settings: providers (Import CSV and Add provider open their dialogs from the
  link), payers (Add payer likewise), the checks as switches saved in place, invitations (one form with
  a row per person, also Team's invite form), security (Use recommended: two-step for every role,
  sign-out after 15 minutes and the access log kept 7 years, the shortest the practice may choose) and
  the plan. Providers are done when the section is complete, payers with an active payer, invitations
  with a second member, the plan when it is active, canceling, past due or managed. Checks and security
  have no stored state that tells a choice from the default, so `practices.setup["first_run"]` records
  when each was first saved, and when the admin hid the steps (`PUT /api/practice/first-run/dismissed`,
  refused until the practice has an active provider). While the practice has no notes the next open
  step holds the screen's one primary button.
- **Setup keeps the admin on an unfinished section.** After a save the screen reads the setup again and
  moves on only when the saved section is now complete; Insurance payers lists the payers above its
  clearinghouse fields. Checks (with level confirmation) and Automatic intake are sections of their own
  instead of panels under every section.
- **The provider dialog shows name, credential, NPI, usual place and email**, with specialty,
  questions by text, active and credentialing behind More, which opens itself when one of its fields
  needs fixing. Email stays in view because the server refuses a provider with no way to receive
  questions, and hiding a required field would trap the admin.
- **Field labels say "NPI, optional"**: a visually hidden comma separates the optional marker.
- **The intake API no longer sends the storage path.** `GET` and `PUT /api/practice/intake` answer the
  settings only, and the section shows whether dropped PDFs are being read. Operators who set up a
  practice's S3 or SFTP access use the practice id they already hold.
- **Setting a password signs in.** `POST /api/auth/password` answers like a password sign-in: a session
  (the refresh cookie set) or the two-step setup challenge when the role needs it, so the page opens the
  app or two-step setup without a second sign-in. A reset link does the same: possession of the link
  already allowed choosing the password and then signing in, and every older session still ends.
- **HQ counts days left from the practice's own calendar day**, as the plan banner does on the server
  (`renews_on` minus today in the practice's time zone), instead of the HQ viewer's local day.
- **The tour follows the new sidebar**: steps still come from `navFor`, the access log step follows
  Insights, the last step lights the account menu, and `TOUR_VERSION` is 2 so everyone sees the new
  layout once.

## Alternatives

- Route groups could have kept `/remittances` and `/quality` with a shared tab layout; nesting the pages
  under their area keeps one rule for active entries and tabs (the address starts with the area's).
- Remembering the dismissed checklist in local storage would show it again on every device and to every
  other admin.
- Comparing the security settings with the recommended ones would have marked a deliberate, stricter
  or looser choice as never done.
- Signing in only after an invite and not after a reset would have needed two answers for one route.

## Follows

- No migration: the first-run marks live in the existing `practices.setup` document.

## Later

- Use recommended now sets sign-out after 7 days without use, not 15 minutes:
  [0063](0063-longer-sign-in.md).
