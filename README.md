# Bodha Coder

Clinical coding review. Bodha Coder reads each visit note, checks the billed codes against the
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

Backend (Python 3.12+):

```
cd backend
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"
copy .env.example .env
alembic upgrade head
python -m app.scripts.bootstrap_hq
uvicorn app.main:app --port 8000 --proxy-headers --forwarded-allow-ips 127.0.0.1
python -m app.worker
```

Frontend (Node 24):

```
cd frontend
npm ci
npm run dev
```

The frontend proxies `/api` to `BACKEND_URL` (default `http://localhost:8000`). Run uvicorn with
`--proxy-headers` and `--forwarded-allow-ips` set to the web server's address so the access log
records the visitor's address, not the proxy's.

## Configuration

All settings are environment variables read by `backend/app/core/config.py`; `.env.example` lists
them. For Cloudflare R2 set `S3_ENDPOINT_URL=https://<account>.r2.cloudflarestorage.com`,
`S3_REGION=auto` and `S3_SERVER_SIDE_ENCRYPTION=` (R2 encrypts at rest itself).

### Email and text messages

| Setting | Values |
|---|---|
| `EMAIL_TRANSPORT` | `ses` (Amazon SES API), `smtp` (any SMTP server over STARTTLS, including the SES SMTP endpoint), `outbox` (writes each message to `MAIL_OUTBOX_DIR`, for local runs) |
| `SMS_TRANSPORT` | `sns` (Amazon SNS), `twilio`, `outbox` |
| `MAIL_FROM` | a sender on a domain verified in SES, for example `Bodha Coder <no-reply@yourpractice.com>` |
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
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | an OAuth 2.0 client of type "Web application" in Google Cloud. Sign in with Google stays off until both are set |

Register `{APP_URL}/api/auth/google/callback` (for example `https://coder.example.com/api/auth/google/callback`)
as the client's authorised redirect URI; requests reach the API through the web server's `/api` proxy.
Google only signs in people who already have a Bodha Coder account with the same email, and two-step
verification still applies to them. Sign-in, password reset, two-step codes, Google returns, provider
codes and demo requests are rate limited per address and account, so uvicorn must see the visitor's
address (`--proxy-headers` and `--forwarded-allow-ips`, above).

### Gemini on Vertex AI

Clinical notes are PHI. Send them to Gemini through Vertex AI, which Google's HIPAA BAA covers; the
Gemini Developer API (`GEMINI_API_KEY`) is for development with made-up notes.

| Setting | Values |
|---|---|
| `GEMINI_BACKEND` | `developer` (default, uses `GEMINI_API_KEY`) or `vertex` |
| `GOOGLE_CLOUD_PROJECT` | the Google Cloud project that holds the signed BAA and has the Vertex AI API enabled |
| `GOOGLE_CLOUD_LOCATION` | a regional endpoint such as `us-central1`, where notes are processed |
| `GEMINI_MODEL` | a Gemini model Vertex serves in that location |

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
check, ruff, the migrations up and down against Postgres, pytest, and the frontend lint, type
check, tests and build.

## Data sources

| Data | Source | Retrieved |
|---|---|---|
| CMS-HCC V28 ICD-10 mapping, relative factors, hierarchies, interactions (`backend/app/codes/data/hcc_v28_2027*`) | CMS PY 2027 initial model software, [py-2027-initial-model-software.zip](https://www.cms.gov/files/zip/py-2027-initial-model-software.zip) (package `CMS_HCC_v28_2027_T1_initial_package_v2`); SHA-256 values in `hcc_v28_2027.meta.json` | 2026-11-26 |
| CMS CY 2026 physician fee schedule RVUs and conversion factor for Medicare national estimates (`backend/app/codes/data/pfs_rvu_2026*`) | CMS PFS Relative Value Files, [RVU26D](https://www.cms.gov/medicare/payment/fee-schedules/physician/pfs-relative-value-files/rvu26d) (October 2026 release, [rvu26d-updated-08-26-2026.zip](https://www.cms.gov/files/zip/rvu26d-updated-08-26-2026.zip)), `PPRRVU2026_Oct_nonQPP.csv` rows with a blank modifier, conversion factor 33.4009; SHA-256 values in `pfs_rvu_2026.meta.json` | 2026-11-27 |

## Reused from ChartMate

ICD-10-CM releases (CDC, public domain), the CMS 2026 physician fee schedule code list (codes
only), the CMS MIPS 2026 catalog and reporting-code table, the practice MIPS list rules, and the
CDI gap, audit checklist, E/M and MIPS review prompts. See
[docs/decisions/0002-reuse-chartmate.md](docs/decisions/0002-reuse-chartmate.md).
