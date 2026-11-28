# 0045 Browser journeys in CI and a nightly production canary

Date: 2026-11-28

Context: pytest drives the API in process with fakes, and vitest renders screens with mocked calls.
Nothing opened the built web app in a browser against a running API, worker, database, object store
and mail, so a break between the two halves (a proxy rule, a cookie, a host mapping, a worker
outcome reaching the wrong lane) reached production unseen, and production itself had no check
beyond the load balancer's health probe.

## Choice

- **Tools.** Playwright 1.65.1 with Chromium's headless shell, and `@axe-core/playwright` 4.14.1,
  as frontend dev dependencies. Journeys live in `frontend/e2e/journeys` (one file per role's day),
  helpers in `frontend/e2e/support`. Tests import the screens' strings from `src`, so the copy keeps
  one home and a reworded label does not break a journey.
- **The stack in CI** (`e2e` job of `ci.yml`): the Postgres 17 service, moto server 5.2.6 as the S3
  store, the API under uvicorn and the worker with `GEMINI_BACKEND=demo` and
  `APP_ENVIRONMENT=staging` (never production: the demo is refused there, [0023](0023-demo-model-backend.md)),
  email and texts written to `MAIL_OUTBOX_DIR`, and the web app from `next build` and `next start`.
  `ADMIN_URL=http://admin.localhost:3000` keeps HQ on its own host as in production
  ([0033](0033-hq-on-its-own-host.md)); `COOKIE_SECURE=false` because the runner serves plain http.
- **Seeding.** Each test calls `python -m tests.e2e_seed <scenario>` (`backend/tests/e2e_seed`) and
  gets its own practice, people, providers and notes, named with a random marker, so tests run in
  parallel and need no clean-up. The seed works through the public API as HQ and the practice admin
  would: HQ adds the practice, the admin invites people, each invitation is accepted from the link in
  the outbox, notes are uploaded and read by the real worker, signatures adopted and claims
  approved. Two steps go to the database instead: the seeding HQ account and enrolled two-step
  secrets are written directly, and access tokens are issued with `services.auth.access_token_for`
  rather than by signing in. Signing in is rate limited per address and per account, a two-step
  code is accepted once per 30-second step, and every browser request reaches the API from the one
  loopback address, so a seed that signed in would starve the journeys of sign-ins. The seed refuses
  `APP_ENVIRONMENT=production` and any model backend but the demo.
- **Synthetic notes.** One-page PDFs from `tests.fakes.text_pdf` with the labels upload matching
  reads (patient, date of service, place of service, provider and NPI). The seed varies the "Return
  in N weeks" line until `demo_outcome` of the extracted text is the outcome the scenario needs, and
  fails when the worker's lane differs from it.
- **Deterministic waits.** No fixed sleeps: tests wait on roles and text, poll the outbox, and reload
  until the worker's result shows (`expect(...).toPass`). There are no retries; a failure is a
  finding.
- **Accessibility.** Every visited page runs axe with the WCAG 2.0 to 2.2 A and AA rules; a serious or
  critical violation fails the journey and lists the rule and the elements.
- **Failure output.** Traces and screenshots are kept only for failed tests and uploaded with the
  server logs. All of it is synthetic.
- **Required.** The job sits in `ci.yml` beside the others under the same repository guard, with no
  `continue-on-error`, so a red journey fails CI like any other job. The public repository has no
  branch protection; making CI block merges is a repository setting, not a file.

## Nightly production canary

- `.github/workflows/canary.yml` runs at 08:17 UTC and on demand, only in `CHARTMATE-APP/bodha-coder`,
  in the `production` environment, with `frontend/e2e/canary/playwright.config.ts`.
- It checks `/api/health/ready` on both hosts, signs in on `www.bodhaai.co` and `admin.bodhaai.co`
  as two canary accounts (password and two-step code from environment secrets), and opens pages
  whose reads write nothing: Today in a practice with no notes, Insights, the four Settings tabs,
  Account and Help; and the HQ overview, practices, organizations, activity, spend, team and demo
  requests. It never opens the queue, inbox, billing, compliance, the access log or a note, because
  those reads write access-log rows.
- A route guard aborts every API request other than GET and HEAD and the three sign-in posts (login,
  two-step verify, refresh) and fails the run listing them; any API answer of 400 or more fails it
  too. It does not sign out, because sign-out writes an event; the session lapses after 30 idle
  minutes and the runner's browser is thrown away.
- It records no trace, screenshot or video, since production pages show real practices.
- What a run still writes: the rate-limit rows of sign-in and two-step, the `signed_in` auth events
  with their mirrors, one session per account and `users.last_active_at` and `mfa_last_step`.

## Alternatives

- **Signing in through the API to seed**: runs into the sign-in and two-step limits above.
- **A seeding endpoint in the API**: would ship in the production image.
- **MinIO or LocalStack for S3**: MinIO no longer publishes free images, and LocalStack needs an auth
  token in CI.
- **Mocked API in the browser**: would not test the stack, which is the point.
- **Retries**: hide flaky journeys instead of fixing them.

## Follows

- [OPERATIONS.md](../OPERATIONS.md#production-canary) lists the canary accounts, secrets and two-step
  setup, to be created after merge.
- `README.md` (Checks), [DEPLOY.md](../DEPLOY.md) and [ARCHITECTURE.md](../ARCHITECTURE.md) describe
  the job and the canary.
