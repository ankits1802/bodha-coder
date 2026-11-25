# Bodha Coder

Clinical coding review. Bodha Coder reads each visit note, checks the billed codes against the
documentation, and sends the note to the right person: ready to approve, needs a coder, ask the
provider, or compliance. Approved codes are exported for billing.

| Part | Stack |
|---|---|
| `frontend/` | Next.js (App Router), React, TypeScript, Tailwind CSS |
| `backend/` | Python, FastAPI, SQLAlchemy, Alembic, Postgres |
| AI | Gemini, one bundled structured call per note (E/M, ICD-10-CM, CDI queries, audit risk, MIPS) |
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

## Checks

Every test, type check and build runs on GitHub Actions (`.github/workflows/ci.yml`): the hygiene
check, ruff, the migrations up and down against Postgres, pytest, and the frontend lint, type
check, tests and build.

## Reused from ChartMate

ICD-10-CM releases (CDC, public domain), the CMS 2026 physician fee schedule code list (codes
only), the CMS MIPS 2026 catalog and reporting-code table, the practice MIPS list rules, and the
CDI gap, audit checklist, E/M and MIPS review prompts. See
[docs/decisions/0002-reuse-chartmate.md](docs/decisions/0002-reuse-chartmate.md).
