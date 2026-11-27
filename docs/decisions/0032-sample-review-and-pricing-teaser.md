# 0032 Sample review and pricing teaser on the landing page

Date: 2026-11-28

Context: the landing page showed what Bodha does only in pictures, and named no price. Visitors could not
try a review before signing up, and the plan catalog was read only by `/pricing`.

## Choice

- "Try it on a sample note." sits after the story, so the review it describes is the next thing a visitor
  can do; the numbers band then separates it from the role tabs. Three synthetic notes, each labelled
  Sample note and naming no person, show a level billed one too high (99214 to 99213 for one acute,
  uncomplicated illness with no data reviewed), a level billed one too low with the G2211 add-on missed,
  and diagnoses coded without their detail (E11.22, N18.31 with HCC 329 in CMS-HCC V28, I12.9).
- Each review is static data in `features/landing/sample/samples.ts`, written by hand. A live model run
  on the public page was rejected: it would cost a model call per visitor, invite real patient notes into
  an unauthenticated form and make the demo depend on the API. A test checks every evidence quote against
  its note and every changed code against the billed codes.
- `y` and `n` act only while focus is inside the review panel, reusing the note review shortcuts from the
  shortcut registry; a page-wide listener was rejected because the landing page is read with the keyboard
  and `n` would decide a finding the visitor never chose.
- The pricing teaser shows the trial and every plan priced per provider, worded by the shared
  `cardPrice`. The home route reads the catalog on the server with `loadPlanCatalog`, as `/pricing`
  does ([0031](0031-pricing-rendered-on-the-server.md)), and is rendered per request; without a catalog the
  teaser fetches it in the browser. `pricing/CatalogView.tsx` holds that choice once for both pages.
- `useRovingTabs` and `tabKeys` moved from `desks/` to `landing/tabs/`, since the role tabs and the sample
  tabs share them.

## Follows

- The home page now needs `BACKEND_URL` at request time like `/pricing`, and shows the same prices within
  the same hour.
- A sample note is changed only together with its expected codes in `sampleClaim.test.ts`, checked against
  the code set and E/M rules by hand.
