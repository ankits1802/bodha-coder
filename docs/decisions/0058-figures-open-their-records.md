# 0058 A dashboard figure opens the records it counts

Date: 2026-11-28

Context: the owner asked that the figures on the dashboards be clickable and lead to the records they
count, on HQ and on the practice side ("the number of organizations, when I click it, should open the
organizations tab"). Today's lane tiles already linked, each with its own link styling; no other figure
did, and nothing guaranteed that a figure and the list it would open count the same records.

## Choice

- One component. `StatCell` takes an `href`. With one, the whole cell is a `next/link` anchor named by
  its label, figure and note with pauses ("Organizations, 3"; "Waiting, 12, 3 reading now"), so the name
  holds every visible word as the design asks, with the row-hover background and an inset focus ring (the
  grid clips an outer one). The name is an `aria-label`: a name taken from the cell's content depends on
  how each browser joins its stacked lines, with or without a space or the pause. Figures keep the label
  colour; the action purple stays on the primary button. `StatGrid` takes `size` (`lg` for Today's lanes), and `StatCell` takes
  `tone` for a lane's dot, so Today's tiles are `StatCell`s and lose their own link styles. A linked
  value and note are text, so the name can be built from them; TypeScript refuses a link on a figure
  drawn as a component.
- One rule for a link. A figure links only when a list screen shows exactly its records, with the filter
  in the address, and the figure is counted by the same query or function as that list:

  | Figure | Opens | Shared definition |
  |---|---|---|
  | HQ Organizations (new) | `/hq/organizations` | `hq_organizations.organization_count` counts the select `organization_rows` lists |
  | HQ Practices | `/hq/practices?status=live` (new filter, Live) | active or trial: `ACTIVE_PRACTICE_STATUSES` on the server, `isLive` on the list |
  | HQ Model cost this month (new) | `/hq/spend?from=…&to=…` for the month so far | `expenditure.month_to_date` is the `expenditure` report the spend page reads, with its range |
  | Today's lanes | the queue lane, or `/compliance` for those who can open it | both count the lane's ready notes (`lane_counts`; `queue_query` with the lane, which `/compliance` also reads) |
  | Billing Ready to bill | `/billing` | the summary counts with `billing_total` over the list's filter |
  | Billing Exported today (new filter) | `/billing?show=today` | the same, with `exported_within` the practice's day |

- Plain text otherwise: a rate, a median or a money estimate; a figure over a rolling 24 hours, a period
  of Insights or every practice of an organization, which no list holds; a total of the table directly
  below it (spend, usage, evaluation cases, sample facts); and any figure whose list the viewer cannot
  open. `reachableHref(user, area, href)` gives the address only when `canReach` allows it, so a viewer's
  lane tiles and every figure in a billing-only session stay text.
- Billing's Ready to bill used to count approved notes not exported, and Exported today every note
  exported in the day; both now count the list's own query (approved or exported, with an approved claim),
  so a note reopened after export no longer counts as exported today.
- The HQ overview's grid is labelled Platform, since it now holds more than the last 24 hours.

## Left as they are

- Held for provider counts notes with a sent request that holds the claim, approved or not; Ready to bill
  marks only approved visits held for a level confirmation, and the unapproved ones sit in the provider
  lane among requests that hold nothing. No list holds exactly those notes, so it stays text.
- Plan usage (users and providers against the limit) stays text: Team also lists blocked members and
  Setup lists inactive providers, which the plan does not count.
- Insights counts notes read or approved in a period; the queue lists open work and Ready to bill lists
  visits by service date, so neither shows those notes.

## What follows

A new figure states its destination with the list's own filter and counts with that list's query, or
stays text. Adding a filter to a list for a figure means putting it in the list's address and on the
screen, and counting the figure with the same function.
