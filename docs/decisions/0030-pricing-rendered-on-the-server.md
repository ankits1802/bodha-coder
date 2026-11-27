# 0030 Pricing rendered on the server

Date: 2026-11-27

Context: `/pricing` fetched `GET /api/plans` in the browser, so its HTML held a loading state and no plan
names or prices for search engines to read.

## Choice

- The page is rendered per request (`dynamic = "force-dynamic"`) and reads the catalog on the server with
  `lib/api/planCatalogServer.loadPlanCatalog`, at `BACKEND_URL` through `lib/backend.backendUrl`, the one
  home of that address, which `next.config.ts` also imports for its rewrites. The fetch is kept for an hour
  in the Next.js data cache (`next.revalidate`), so most requests reach the API at most hourly, and gives
  up after three seconds.
- Static or incremental rendering was rejected: the Docker build has no API (`BACKEND_URL` is a
  placeholder), so the build would cache a page without prices until its first revalidation after every
  release. Rendering per request fetches nothing at build.
- When the API cannot be reached or answers an error, `loadPlanCatalog` returns `null` and the page renders
  the existing browser fetch, with its loading, error and retry states. This is the one deliberate
  fallback: the page is public and must never fail because the catalog is late.
- With a catalog, the page adds one `application/ld+json` script: a schema.org `Product` for each plan
  priced per provider (Essentials, Professional), each with a monthly and a yearly `Offer` in USD whose
  `UnitPriceSpecification` names the unit as on the cards. `<` is escaped so the JSON cannot close the
  script.

## Follows

- The web server needs `BACKEND_URL` at run time as well as at start; the image already requires it.
- A price changed in `services/plans.py` reaches the HTML within an hour; a new web task starts with an
  empty cache and reads the catalog on its first request.
