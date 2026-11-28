# Project bindings

The only project-specific file of the three practice skills (`engineering-practices`,
`backend-practices`, `frontend-practices`). The rules live in the skills; the facts below change
with the project. Review this file whenever the layout, tooling or commands change.

Last reviewed: 2026-11-28.

## What this repository is

Bodha Assure: a web application that reads clinical visit notes (PDF), checks the billed medical
codes (E/M CPT, ICD-10-CM, modifiers) against the documentation with Gemini, and routes each note
to a person: ready to approve, needs a coder, ask the provider (CDI query and signed addendum), or
compliance. Approved codes are exported for billing. Practices are tenants; Bodha HQ runs the
platform. Web only. The previous application is kept outside version control in `legacy/`.

## Layout and layers

```
backend/app/core/       shared layer: settings, database engine and sessions, security, errors,
                        roles, account realms and request sites, request guards (current user, roles, provider sessions)
backend/app/models/     SQLAlchemy models: the declarative base and the tables
backend/app/codes/      code sets and their pure logic: ICD-10-CM releases (CDC data with
                        checksummed manifests), E/M families, CPT and HCPCS code list (CMS PFS,
                        codes only), places of service, NPI check digit, CMS MIPS 2026 catalog,
                        reporting codes and the practice MIPS scope (vendored from ChartMate), and the
                        rules for measures a practice defines itself
backend/app/ai/         the model contract (contracts.py), prompts, report models and the
                        bundled review call (review.py); talks to a ModelClient, never to a SDK
backend/app/adapters/   one adapter per external service: Gemini, S3/R2 object store,
                        SMTP/Twilio messenger, PDF text, Stripe and PayPal (one billing contract),
                        EHRs over FHIR (guarded outbound HTTP, SMART backend services, FHIR client)
backend/app/services/   domain services: findings and routing (pure), analysis pipeline,
                        uploads, review actions, addenda, auth, team, practice setup, worklists,
                        billing (claims export), plans and subscriptions, insights, note view, HQ,
                        audit logs, practice measures, usage timing, the EHR connection and pull
backend/app/api/        entry points: request bodies, wiring, routes/<area>.py (thin handlers),
                        responses/<area>.py (the response model of every JSON route)
backend/app/worker.py   the analysis worker process (python -m app.worker)
backend/app/scripts/    entry points: bootstrap_hq, invite_hq
backend/app/main.py     the ASGI app
backend/alembic/        migrations; 0001 executes a frozen DDL file compiled from the models
backend/tests/          tests; they run on GitHub Actions against Postgres
backend/tests/e2e_seed/ the synthetic seed the browser journeys call (python -m tests.e2e_seed)
frontend/               Next.js App Router web client
frontend/e2e/           Playwright: journeys/ (CI), canary/ (nightly, production), support/
tools/                  hygiene_check.py and its baseline, export_openapi.py (frontend/openapi.json)
infra/ses_intake/       the email intake Lambda function (deployed on its own; standard library and boto3)
docs/                   living documents and the decision log
```

Imports in `backend/app` point one way, enforced by `LAYER_IMPORTS` in `tools/hygiene_check.py`:

```
main     -> api, adapters, codes, core
worker   -> services, adapters, ai, codes, core, models
scripts  -> services, adapters, core, models
api      -> services, adapters, codes, core, models
services -> ai, adapters, codes, core, models
adapters -> ai, core
ai       -> codes, core
core     -> models
codes    -> (nothing else)
models   -> (nothing else)
```

Frontend source (`frontend/src`): `app/` routes, `components/ui/` generic primitives,
`components/shared/` domain pieces used by two or more features, `features/<feature>/` one folder
per screen, `lib/` the one API client, session, formatters and roles. API types come from the backend:
`lib/api/schema.ts` is generated from `openapi.json`, and `lib/api/types.ts` names its schemas for the screens.

## Shared layer and its catalogue

The shared layer is `backend/app/core/` with `backend/app/codes/` for code-set logic. The
catalogue is `docs/CORE_API.md`: check it before writing any helper.

## Budgets

| Unit | Budget (a trigger to split, not a wall) |
|---|---|
| Python file | about 400 lines |
| function or method | about 40 lines |
| parameters | 5 positional, options keyword-only |
| nesting depth | 3 |
| UI component file | about 150 lines |

Modules vendored from ChartMate (`codes/cms_mips_2026.py`, `codes/catalog_pfs.py`,
`codes/mips_catalog.py`, `codes/mips_reporting_codes.py`) are exempt from budgets, line length and
formatting so they stay comparable line for line with their source. Existing code over budget is recorded in
`tools/hygiene_baseline.json` and may only shrink.

## Commands

The owner's rule: every test, type check and build runs on GitHub Actions only (`.github/workflows/ci.yml`).
A development machine runs the formatters, the linters and the hygiene check.

| Purpose | Command |
|---|---|
| hygiene check (ratchet) | `python tools/hygiene_check.py` |
| accept a lower baseline after a clean-up | `python tools/hygiene_check.py --update-baseline` |
| backend lint and format | `cd backend; .venv\Scripts\python.exe -m ruff check .` and `... -m ruff format .` |
| tools and infra lint and format | `backend\.venv\Scripts\python.exe -m ruff check tools infra` and `... -m ruff format tools infra` |
| frontend lint | `cd frontend; npm run lint` |
| regenerate the API types after an API change | `backend\.venv\Scripts\python.exe tools\export_openapi.py`, then `cd frontend; npm run api:types` |
| CI only: backend tests | `pytest -q` after `alembic upgrade head` against the Postgres service |
| CI only: frontend | `npm run typecheck`, `npm test`, `npm run build` |
| CI only: browser journeys | `npx playwright test` in `frontend` once the stack of the `e2e` job is up |
| nightly, production only | `npx playwright test --config e2e/canary/playwright.config.ts` (`canary.yml`) |

## Version control

Git, `main` on GitHub (public; `legacy/` is never committed). Agents commit and push only when the
owner asks.

## Living documents

| Document | Must stay true about |
|---|---|
| `README.md` | what Bodha Assure is, how to run and deploy it |
| `docs/ARCHITECTURE.md` | layers, data model, how a note flows, storage |
| `docs/CORE_API.md` | the catalogue of shared components |
| `docs/DESIGN.md` | the design system every screen follows |
| `docs/decisions/` | decision log: one short file per decision, numbered |
| `docs/TECH_DEBT.md` | debt register |

## Rules from the owner that override the skills

- **No code comments at all**, and no docstrings, in any language. The why goes in
  `docs/decisions/`; an exception in `docs/TECH_DEBT.md`. Only functional directives stay (`noqa`,
  `type: ignore`). `tools/hygiene_check.py` enforces it.
- Latest stable dependency versions, pinned (`backend/pyproject.toml`, `frontend/package-lock.json`).
- Secret values are never printed, logged, committed or put in fixtures.
- Tests run on GitHub only.
- Design: Apple system font only (Inter where SF is unavailable); dark purple only on the
  primary action button; no explanatory helper copy.

## Domain rules that outrank convenience

- Never suggest a code the documentation does not support; a code Bodha cannot confirm is shown
  for review, never as a fix. ICD-10-CM codes are checked against the release for the date of
  service; CPT codes against the CMS fee schedule list.
- Every model run, suggestion with its reasoning and evidence, decision, code-set change, provider
  answer and note revision is stored as its own record and never overwritten.
- Provider queries are non-leading and carry no money or reimbursement wording; the addendum is
  built only from the provider's own answers.
- PHI never appears in object keys, URLs, logs or messages; every PHI read, change and export is
  written to the access log.
- A guard (tenant, role, provider session, approval hold, separation of duties) fails closed.
