# 0033 HQ on its own host, with its own accounts

Date: 2026-11-28

Context: the HQ console shared the product's host, its sign-in and its account space: one email meant
one account, and one Google, Microsoft or Yahoo subject one user. The owner runs Bodha HQ and also uses
the product as a practice, with the same email and the same Google account, and wants HQ at
`admin.bodhaai.co` apart from `www.bodhaai.co`. Only one HQ account existed (the bootstrap one), and the
owner wants five HQ owners.

## Choice

- **Two realms.** `users.realm` is `hq` for the `hq` role and `practice` for every other role, computed by
  Postgres from `role` (a stored generated column), so no code path can set it wrongly. Emails are unique
  per realm (`(email, realm)`), and `user_identities` carries the realm too, unique per
  `(provider, subject, realm)`, with a foreign key on `(user_id, realm)` to `users (id, realm)` so a link
  can never claim the other realm. A stored column was chosen over an expression index so the uniqueness
  and the foreign key are plain constraints that `alembic check` compares.
- **The host decides the realm, on the server.** `ADMIN_URL` (empty by default) names the HQ host.
  `core.realms.request_site` turns a request into a `Site`: its address (`ADMIN_URL` or `APP_URL`) and the
  realms it serves. The `ADMIN_URL` host serves `hq` only; any other host serves `practice` only; with
  `ADMIN_URL` empty one site on `APP_URL` serves both, which keeps local and single-host setups as they
  were. An unknown host is a practice host, so HQ is reachable only on the exact admin host.
- **Which host header.** On AWS the CDN and the load balancer forward the browser's `Host` to the API.
  Through the web server's `/api` rewrite (local development, Compose) `Host` is the API's own address
  and Next.js sets `X-Forwarded-Host` to the browser's host, overwriting any the browser sent. The API
  uses `Host` when it is one of the two configured hosts; otherwise it uses `X-Forwarded-Host` only when
  the request's address is in `FORWARDED_ALLOW_IPS`, the same setting uvicorn reads. Uvicorn has already
  replaced that address with the visitor's when a trusted proxy sent `X-Forwarded-For`, so a request
  relayed by the load balancer is judged by the visitor's address and its `X-Forwarded-Host` is ignored;
  the rewrite sends no `X-Forwarded-For`, so its own address is judged. The realm is not a privilege in
  any case: credentials still decide, and every URL the API builds comes from `APP_URL` or `ADMIN_URL`,
  never from a header.
- **Every account lookup stays in the site's realms**: password sign-in, the two-step steps, refresh,
  forgot password, setting a password from a link, the OpenID Connect callback and every authenticated
  request (`session_actor` answers 401 for a user of another realm). An HQ account cannot sign in on the
  main host, a practice account cannot sign in on the HQ host.
- **Links follow the account**: invites and password resets use `ADMIN_URL` for HQ users and `APP_URL`
  for practice users (`core.realms.realm_url`).
- **OpenID Connect redirect URIs follow the host the flow started on.** The start keeps the site in the
  signed `bodha_oidc` cookie; the callback refuses a different site and exchanges the code with the same
  redirect URI. The adapter takes the redirect URI per call instead of fixing it at start-up. Each service
  needs both callbacks registered.
- **Self sign-up exists only where the `practice` realm is served.** On the HQ host `/api/signup` answers
  404, `GET /api/auth/providers` reports sign-up off, and an unknown identity gets `no_account`.
- **Cookies stay host-only.** The refresh, sign-in and sign-up cookies never carried a `Domain`; tests now
  hold them to it, so the two hosts never share a session.
- **HQ hardening is unchanged and applies on the HQ host**: two-step verification for every HQ account
  (already required by the sign-in policy) and the 15-minute idle sign-out.
- **One email, one account when there is one host.** With `ADMIN_URL` empty, creating an account (team
  invite, HQ practice, self sign-up, HQ invite, bootstrap) refuses an email either realm uses, as before.
  If two accounts share an email after `ADMIN_URL` is emptied again, sign-in by that email reaches neither
  (it fails closed) until `ADMIN_URL` is set again or one of the two is removed.
- **The web server routes pages by host.** `src/proxy.ts` reads `ADMIN_URL` and `SITE_URL` at request
  time. On the HQ host it serves `/hq` and the shared sign-in, forgot-password and set-password pages,
  sends `/` to `/hq` (the session gate sends a visitor without a session to sign-in) and sends everything
  else to the main host; on any other host it sends `/hq` to the HQ host. It reads the `Host` header,
  because Next.js builds the request URL from its own listening address.
- **An HQ team.** `/hq/team` lists, invites, re-invites, deactivates and reactivates HQ accounts. Invites
  reuse the practice invite (`team.send_invite`) and the set-password page, scoped to the HQ realm with
  the link on `ADMIN_URL`. Deactivating yourself is refused, and so is deactivating the last active HQ
  account; the check locks every HQ row (and re-reads them) so two owners deactivating each other at once
  cannot leave none. Each action writes HQ activity.
- **`python -m app.scripts.invite_hq`** does the same from a one-off task: new people are invited, pending
  invites resent, active accounts left alone, and an existing account whose name differs is renamed (the
  bootstrap account is "Bodha Admin"). It prints one line per person with the name, the outcome and the
  user id, never an email, password or token. Scripts may now call services and adapters, like the API and
  the worker (`LAYER_IMPORTS` in `tools/hygiene_check.py`), so the script sends invites through the same
  service function as the page.

## Follows

- Migration 0010 adds the columns and constraints. `user_identities.realm` defaults to `practice` in the
  database so the release before 0010 can still link practice accounts during a rolling deploy. The
  default stays: the code always names the realm, and a link that leaves it out for an HQ user fails the
  foreign key instead of landing in the wrong realm.
- When `ADMIN_URL` is first set, HQ users sign in again on the HQ host, and HQ invites or resets sent
  earlier (linked to the main host) stop working and must be sent again.
- The owner registers `https://admin.bodhaai.co/api/auth/{google,microsoft,yahoo}/callback` beside the
  existing callbacks, and routes the HQ host to the same services with the viewer's `Host` forwarded
  ([DEPLOY.md](../DEPLOY.md#hq-on-its-own-host)).
