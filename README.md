# Bodha Assure

Clinical coding review. Bodha Assure reads each visit note, checks the billed codes against the
documentation, and sends the note to the right person: ready to approve, needs a coder, ask the
provider, or compliance. Approved codes are exported for billing.

| Part | Stack |
|---|---|
| `frontend/` | Next.js (App Router), React, TypeScript, Tailwind CSS |
| `backend/` | Python, FastAPI, SQLAlchemy, Alembic, Postgres |
| AI | Gemini (Vertex AI for PHI, or the Developer API), one bundled structured call per note (E/M with modifiers and add-on codes, ICD-10-CM, CDI queries, audit risk, MIPS, risk adjustment) |
| Files | S3 or Cloudflare R2 (any S3-compatible store) |

## How a note moves

1. A coder uploads the day's PDFs for one provider and date of service. Date, patient and billed
   code are read from file names like `2026-11-25 - REYES MARISOL - 99215 - Progress.pdf`.
2. The worker reads the PDF (text layer, or the PDF itself for scans), runs the review and stores
   the result as a new analysis revision with every suggestion, its reasoning and its evidence.
3. The note lands in a lane. A coder accepts or keeps each suggestion, asks the provider, flags
   it for compliance, or approves it.
4. A provider opens a secure link, confirms a one-time code, answers, and signs an addendum; the
   note is read again with the addendum.
5. Approved notes appear in Ready to bill and are exported as CSV.

Details: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Run it

Backend (Python 3.14):

```
cd backend
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.lock
.venv\Scripts\python.exe -m pip install --no-deps -e .
copy .env.example .env
alembic upgrade head
python -m app.scripts.bootstrap_hq
uvicorn app.main:app --port 8000 --proxy-headers --forwarded-allow-ips 127.0.0.1
python -m app.worker
```

`backend/requirements.lock` pins every Python package, direct and transitive, for Linux images and
Windows alike; CI and the backend image install from it. After changing `pyproject.toml`, compile it
again from `backend` with uv 0.13.10 (installed in a separate environment):

```
uv pip compile pyproject.toml --extra dev --universal --python-version 3.14 --no-header --no-annotate -o requirements.lock
```

Add `--upgrade` to move every pin to its latest release. CI fails when the lock and `pyproject.toml`
disagree.

Frontend (Node 24):

```
cd frontend
npm ci
npm run dev
```

The frontend proxies `/api` to `BACKEND_URL` (default `http://localhost:8000`), and its server reads the
plan catalog from there to render `/` and `/pricing`. Run uvicorn with
`--proxy-headers` and `--forwarded-allow-ips` set to the web server's address so the access log
records the visitor's address, not the proxy's.

### API types

Every JSON route declares a response model (`backend/app/api/responses/`), and the frontend's API
types are generated from the OpenAPI document. After changing a route, a response model or a request
body, regenerate both files from the repository root and commit them:

```
backend\.venv\Scripts\python.exe tools\export_openapi.py
cd frontend
npm run api:types
```

The first writes `frontend/openapi.json` (no database or secrets needed), the second
`frontend/src/lib/api/schema.ts`. Screens import the named types in `frontend/src/lib/api/types.ts`,
which alias the generated schemas. CI regenerates both and fails when either differs.

## Configuration

All settings are environment variables read by `backend/app/core/config.py`; `.env.example` lists
them. For Cloudflare R2 set `S3_ENDPOINT_URL=https://<account>.r2.cloudflarestorage.com`,
`S3_REGION=auto` and `S3_SERVER_SIDE_ENCRYPTION=` (R2 encrypts at rest itself).

### Email and text messages

| Setting | Values |
|---|---|
| `EMAIL_TRANSPORT` | `ses` (Amazon SES API), `smtp` (any SMTP server over STARTTLS, including the SES SMTP endpoint), `outbox` (writes each message to `MAIL_OUTBOX_DIR`, for local runs) |
| `SMS_TRANSPORT` | `sns` (Amazon SNS), `twilio`, `outbox` |
| `SNS_ORIGINATION_NUMBER` | the toll-free or 10DLC number registered in AWS End User Messaging SMS that SNS texts come from; texts are offered only once it is set (or, for Twilio, `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN` and `TWILIO_FROM`), and always in development |
| `MAIL_FROM` | a sender on a domain verified in SES, for example `Bodha Assure <no-reply@yourpractice.com>` |
| `AWS_MESSAGING_REGION` | the SES and SNS region, for example `us-east-1` |
| `SES_CONFIGURATION_SET` | optional, to track bounces and complaints |

SES and SNS use the standard AWS credential chain: an IAM role on the server, or `AWS_ACCESS_KEY_ID` and
`AWS_SECRET_ACCESS_KEY`. The role needs `ses:SendEmail` and, for texts, `sns:Publish`. Move the SES
account out of the sandbox and verify the sending domain (SPF, DKIM, DMARC) before inviting real users.
Every email is sent as plain text with an HTML version; no message contains patient details.

### Sign-in and two-step verification

| Setting | Values |
|---|---|
| `MFA_ENCRYPTION_KEY` | a Fernet key that encrypts every two-step secret at rest; required once anyone sets up two-step verification. Generate one with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` and keep it with the other secrets: losing it means everyone sets up two-step again. A comma-separated list rotates keys without an outage (see `docs/OPERATIONS.md`) |
| `ADMIN_URL` | the HQ console's own host, for example `https://admin.bodhaai.co`; empty keeps HQ on `APP_URL`. With it set, HQ accounts sign in only there and practice accounts only on `APP_URL`, so one email can hold both; locally use `http://admin.localhost:3000`, and give the web server the same `ADMIN_URL` and `SITE_URL`. More HQ owners are invited on `/hq/team` or with `python -m app.scripts.invite_hq "Full Name <email>"` ([0033](docs/decisions/0033-hq-on-its-own-host.md)) |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | an OAuth 2.0 client of type "Web application" in Google Cloud. Sign in with Google stays off until both are set |
| `MICROSOFT_CLIENT_ID`, `MICROSOFT_CLIENT_SECRET`, `MICROSOFT_TENANT` | an Entra ID app registration (tenant `common` by default). Sign in with Microsoft stays off until the id and secret are set |
| `YAHOO_CLIENT_ID`, `YAHOO_CLIENT_SECRET` | a Yahoo app with OpenID Connect. Sign in with Yahoo stays off until both are set |
| `SELF_SIGNUP_ENABLED`, `TRIAL_DAYS`, `TRIAL_SEATS` | self sign-up on or off (on by default), and the length (14 days) and seats (5) of a new trial |
| `TERMS_URL`, `BAA_URL`, `PRIVACY_URL`, `AGREEMENT_VERSION` | the documents a new practice agrees to and the version stored with its acceptance. Production refuses to start self sign-up without the terms and the BAA |
| `SIGNING_KEY_ID` | the AWS KMS key (ARN of an `ECC_NIST_P256` sign and verify key) that seals every signed approval, compliance decision, provider statement and sign-up agreement. Production refuses to start without it; elsewhere an unset key seals with a fixed development key that production never accepts. Anyone can check a seal at `/verify` ([0040](docs/decisions/0040-e-signatures-and-sealed-records.md)) |

Register `{APP_URL}/api/auth/{provider}/callback` (for example
`https://www.bodhaai.co/api/auth/microsoft/callback`) as each service's redirect URI, and
`{ADMIN_URL}/api/auth/{provider}/callback` as well when `ADMIN_URL` is set; requests reach
the API through the web server's `/api` proxy. The addresses for every environment are in
[docs/DEPLOY.md](docs/DEPLOY.md#self-sign-up-and-sign-in-services).

A practice can start a free trial at `/sign-up`, with its work email or with Google, Microsoft or
Yahoo. The email path sends a set-password link (an email that already has an account gets an email
asking to sign in and add the practice from `/practices/new` instead, and the page answers the same
way); the other path asks for the practice name and time zone and goes straight to two-step setup,
making an existing account with that email the new practice's admin. A trial practice has
`TRIAL_SEATS` seats until `TRIAL_DAYS` after sign-up, and HQ sees it marked "Self sign-up". A sign-in
service signs in an existing account with the same verified email and binds that service's account
to it; two-step verification still applies. With `SELF_SIGNUP_ENABLED=false` only existing accounts
sign in and HQ adds every practice.

One account can belong to several practices, with a role in each: inviting an email that already has
an account adds that practice to it, and the person switches practices from the top of the sidebar and
sees their practices, and can leave one, in the account menu on their name and on the Account page. Blocks, plan limits, the plan-ended rule
and two-step requirements apply per practice
([0037](docs/decisions/0037-multi-practice-membership.md)). Sign-in, sign-up, password reset, two-step codes, service returns,
provider codes and demo requests are rate limited per address and account, so uvicorn must see the
visitor's address (`--proxy-headers` and `--forwarded-allow-ips`, above).

A group with several locations can be one organization: HQ groups the practices and names its admins,
who see every practice, its plan and combined insights, add locations and people, and can pay for the
practices together with one subscription billed per active provider across them. Being an organization
admin opens no practice's records; an audited, emailed self-grant does. A practice or organization that
verifies its email domain (a DNS TXT record or a link to an admin mailbox) can let colleagues who sign up
with that domain ask to join or join automatically
([0044](docs/decisions/0044-organizations-and-domain-join.md)).

Besides the CMS quality measures, a practice admin can add measures of the practice's own (an internal
measure, a payer programme or a registry measure) that the review checks like any other and shows apart
from CMS ones. Bodha also times the work without patient data (how long a note stays open in review, the
inputs per decision and where people pause); practice admins see medians by role and step under
Insights, Usage, and HQ sees them across practices
([0045](docs/decisions/0045-practice-measures-and-usage-timing.md)).

### Plans and billing

| Setting | Values |
|---|---|
| `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_*` | card payments through Stripe Checkout and the Billing Portal; offered once the key, the webhook secret and all four price ids are set |
| `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`, `PAYPAL_WEBHOOK_ID`, `PAYPAL_ENVIRONMENT`, `PAYPAL_PLAN_*` | PayPal subscriptions; offered once the app credentials, the webhook id and all four plan ids are set |
| `BILLING_GRACE_DAYS` | days of access after a failed payment (7) |

Admins choose a plan on `/settings/plan` (Settings, Plan); prices and limits live in `backend/app/services/plans.py`, and only
verified webhooks change a subscription. Setting up the products, prices, portal and webhooks:
[docs/DEPLOY.md](docs/DEPLOY.md#set-up-stripe-and-paypal).

### Gemini on Vertex AI

Clinical notes are PHI. Send them to Gemini through Vertex AI, which Google's HIPAA BAA covers; the
Gemini Developer API (`GEMINI_API_KEY`) is for development with made-up notes.

| Setting | Values |
|---|---|
| `GEMINI_BACKEND` | `developer` (default, uses `GEMINI_API_KEY`), `vertex`, or `demo` (canned reviews of synthetic notes, no model call; refused when `APP_ENVIRONMENT` is `production`) |
| `APP_ENVIRONMENT` | `production` (default), `staging` or `development` |
| `GOOGLE_CLOUD_PROJECT` | the Google Cloud project that holds the signed BAA and has the Vertex AI API enabled |
| `GOOGLE_CLOUD_LOCATION` | a regional endpoint such as `us-central1`, where notes are processed |
| `GEMINI_MODEL` | a Gemini model Vertex serves in that location |
| `MODEL_PRICES` | a JSON object from model name to `{"input": …, "output": …}` in USD per million tokens, used to keep what each review cost and shown on HQ's Spend page; defaults to `gemini-3.8-flash` at 0.50 and 3.00, an estimate to set from Google's price list ([0035](docs/decisions/0035-model-spend-per-provider.md)) |

Vertex uses Application Default Credentials: the service account attached to the worker on Google
Cloud, workload identity federation elsewhere, or `GOOGLE_APPLICATION_CREDENTIALS` pointing at a key
file kept outside the repository. Grant the account the Vertex AI User role. Never put credentials
in `.env` values that are committed. PDFs are sent inline (up to 50 MiB); a larger one fails with
"PDF too large for Vertex inline; split it". See
[docs/decisions/0012-vertex-ai.md](docs/decisions/0012-vertex-ai.md).

## Deploy

`backend/Dockerfile` builds one image for the API, the worker and migrations; `frontend/Dockerfile`
builds the web image, which takes `BACKEND_URL` at start. CI builds both on every push. For a local
or staging stack with Postgres and LocalStack:

```
copy .env.compose.example .env.compose
docker compose --env-file .env.compose up --build
```

The AWS reference deployment (ECS on Fargate, RDS, S3, SES, SNS, Secrets Manager, CloudWatch) is in
[docs/DEPLOY.md](docs/DEPLOY.md), the runbooks in [docs/OPERATIONS.md](docs/OPERATIONS.md), and the
staging load test in [tools/load/README.md](tools/load/README.md).

## Checks

Every test, type check and build runs on GitHub Actions (`.github/workflows/ci.yml`): the hygiene
check, the Python lock against `pyproject.toml`, ruff, the OpenAPI document and the generated
frontend types against the code, the migrations up and down against Postgres, pytest, the
frontend lint, type check, tests and build, and the browser journeys.

The `e2e` job builds the web app (`next build`, `next start`) and runs it with the API and the worker
on the demo model, Postgres, moto as the S3 store and mail written to an outbox, with HQ on
`http://admin.localhost:3000`. Playwright (`frontend/e2e/journeys`) then drives each role's day in
Chromium: self sign-up, the admin's first day, upload and the queue, a coder's review by keyboard,
asking the provider, a compliance return, the claim-lines export, switching practices and the
organization area, HQ, the public verify page, and a rehearsal of the nightly production canary, with
axe on every page. Each test seeds its own synthetic practice through
`python -m tests.e2e_seed <scenario>` (`backend/tests/e2e_seed`); failed tests keep a trace and a
screenshot. A nightly workflow (`.github/workflows/canary.yml`) signs in to
production read-only as two canary accounts
([docs/OPERATIONS.md](docs/OPERATIONS.md#production-canary),
[0049](docs/decisions/0049-browser-journeys-and-production-canary.md)).

## Data sources

| Data | Source | Retrieved |
|---|---|---|
| CMS-HCC V28 ICD-10 mapping, relative factors, hierarchies, interactions (`backend/app/codes/data/hcc_v28_2027*`) | CMS PY 2027 initial model software, [py-2027-initial-model-software.zip](https://www.cms.gov/files/zip/py-2027-initial-model-software.zip) (package `CMS_HCC_v28_2027_T1_initial_package_v2`); SHA-256 values in `hcc_v28_2027.meta.json` | 2026-11-26 |
| CMS CY 2026 physician fee schedule RVUs and conversion factor for Medicare national estimates (`backend/app/codes/data/pfs_rvu_2026*`) | CMS PFS Relative Value Files, [RVU26D](https://www.cms.gov/medicare/payment/fee-schedules/physician/pfs-relative-value-files/rvu26d) (October 2026 release, [rvu26d-updated-08-26-2026.zip](https://www.cms.gov/files/zip/rvu26d-updated-08-26-2026.zip)), `PPRRVU2026_Oct_nonQPP.csv` rows with a blank modifier, conversion factor 33.4009; SHA-256 values in `pfs_rvu_2026.meta.json` | 2026-11-27 |
| CMS CY 2025 E/M visit services by specialty for the E/M level mix (`backend/app/codes/data/em_specialty_2025*`) | CMS Medicare Part B, [Evaluation and Management (E/M) Codes by Specialty reports](https://www.cms.gov/data-research/statistics-trends-reports/medicare-fee-service-parts-b/medicare-utilization-part-b/evaluation-management-em-codes-specialty-reports) (page modified 2026-08-28), [cy-2025-evaluation-management-em-codes-specialty.xlsx](https://www.cms.gov/files/document/cy-2025-evaluation-management-em-codes-specialty.xlsx-1), allowed services of the office, nursing facility, home and inpatient families (CMS leaves out rows under 11 services); rebuilt with `tools/vendor_em_specialty.py`; SHA-256 values in `em_specialty_2025.meta.json` | 2026-11-27 |
| Medicare NCCI practitioner procedure-to-procedure edits, 2026 Q4 (`backend/app/codes/data/ncci_ptp_2026q4.tsv.gz`) | CMS [Medicare NCCI PTP edits](https://www.cms.gov/medicare/coding-billing/national-correct-coding-initiative-ncci-edits/medicare-ncci-procedure-procedure-ptp-edits), version v323r0 effective 2026-10-01, the four parts `medicare-ncci-2026q4-practitioner-ptp-edits-ccipra-v323r0-f1.zip` to `-f4.zip` combined (2,637,645 edits; 1,749,750 kept: indicator 0 or 1 and in effect on or after 2025-10-01); rebuilt with `tools/fetch_ncci.py`; SHA-256 values in `ncci_practitioner.meta.json` | 2026-11-27 |
| Medicare NCCI add-on code edits, 2026 Q4 (`backend/app/codes/data/ncci_aoc_2026q4.tsv.gz`) | CMS [Medicare NCCI add-on code edits](https://www.cms.gov/medicare/coding-billing/national-correct-coding-initiative-ncci-edits/medicare-ncci-add-code-edits), [add-code-edits-medicare-effective-10012026.zip](https://www.cms.gov/files/zip/add-code-edits-medicare-effective-10012026.zip) (`AOC_V2026Q4-F-MCR.txt`); same manifest | 2026-11-27 |
| Medicare NCCI practitioner services MUE tables, 2025 Q4 to 2026 Q4 (`backend/app/codes/data/ncci_mue_*.tsv.gz`) | CMS [Medicare NCCI MUEs](https://www.cms.gov/medicare/coding-billing/national-correct-coding-initiative-ncci-edits/medicare-ncci-medically-unlikely-edits-mues) and the [MUE archive](https://www.cms.gov/medicare/coding-billing/national-correct-coding-initiative-ncci-edits/medicare-ncci-medically-unlikely-edit-mue-archive), `medicare-ncci-<year>-q<n>-practitioner-services-mue-table.zip` for each quarter: code, MUE value, adjudication indicator; same manifest | 2026-11-27 |

## Reused from ChartMate

ICD-10-CM releases (CDC, public domain), the CMS 2026 physician fee schedule code list (codes
only), the CMS MIPS 2026 catalog and reporting-code table, the practice MIPS list rules, and the
CDI gap, audit checklist, E/M and MIPS review prompts. See
[docs/decisions/0002-reuse-chartmate.md](docs/decisions/0002-reuse-chartmate.md).
