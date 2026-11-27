# Deploy

How Bodha Assure is packaged, run locally with Docker Compose, and deployed on AWS. Day-two
procedures are in [OPERATIONS.md](OPERATIONS.md); the load test is in
[tools/load/README.md](../tools/load/README.md). Decision: [0016](decisions/0016-containers-and-deployment.md).

## Images

| Image | Built from | Base | Runs as | Starts |
|---|---|---|---|---|
| `bodha-coder-api` | `backend/Dockerfile` | `python:3.14.10-slim-trixie` | uid 10001 | `api` (default), `worker`, `migrate`, or any command |
| `bodha-coder-web` | `frontend/Dockerfile` | `node:24.22.3-trixie-slim` | uid 1000 | `node server.js` (Next standalone) |

The API image installs the dependencies pinned in `backend/pyproject.toml` from wheels only (the
build fails rather than compile), then the app itself, in a build stage; the final stage holds the
virtual environment, `alembic.ini`, `alembic/` and `docker-entrypoint.sh`, and no compiler or
source tree. One image serves three roles:

| Command | Runs |
|---|---|
| `api` | `uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips $FORWARDED_ALLOW_IPS --workers $WEB_CONCURRENCY --timeout-keep-alive 65 --timeout-graceful-shutdown 25 --no-access-log` |
| `worker` | `python -m app.worker` |
| `migrate` | `alembic upgrade head` |
| anything else | that command, for example `python -m app.scripts.bootstrap_hq` |

`FORWARDED_ALLOW_IPS` defaults to `127.0.0.1` and `WEB_CONCURRENCY` to `1`. Set
`FORWARDED_ALLOW_IPS` to the addresses of the proxies in front of the API (on AWS, the VPC CIDR) so
rate limits and the access log see the visitor's address. When `GOOGLE_CREDENTIALS_JSON` holds a
Google credential (a service account key or a workload identity federation configuration), the
entrypoint writes it to a private temporary file, points `GOOGLE_APPLICATION_CREDENTIALS` at it and
removes the variable, so Vertex AI credentials can come from Secrets Manager. The image's
`HEALTHCHECK` calls `/api/health`; turn it off for `worker` and `migrate` containers.

The web image is built once and pointed at an API at start: `BACKEND_URL` (required, for example
`http://api:8000`) is written into the standalone server's rewrite table before `node server.js`
starts. Next.js fixes rewrites at build time, so the build uses the placeholder
`http://backend-url.invalid`, records every file that contains it, and fails if
`.next/routes-manifest.json` is not one of them. Only those files and `.next/cache` are writable by
the runtime user. The server also reads `BACKEND_URL` at request time to render `/` and `/pricing` with the plan
catalog (kept an hour in `.next/cache`); nothing is fetched at build.

Neither image contains a secret or an `.env` file; both `.dockerignore` files keep them out of the
build context. Tag images with the git commit SHA, push to ECR with immutable tags and scan on
push. CI builds both images on every push (`images` job) without pushing. Every Python dependency
has arm64 wheels, so `docker buildx build --platform linux/arm64` produces Graviton images when
wanted; CI builds amd64.

## Health and logs

| Endpoint | Answers |
|---|---|
| `GET /api/health` | liveness: `200 {"status": "ok"}` while the process serves requests |
| `GET /api/health/ready` | readiness: `SELECT 1` on the database and `HeadBucket` on the object store, two seconds each; `200` with `{"status": "ready", "checks": {...}}`, or `503` naming the failed check as `unavailable` |

Load balancer and container health checks use liveness. Readiness is for the release smoke check
and synthetic monitoring; never let it restart tasks, or a storage outage restarts every task.

Every process writes one JSON object per line to standard output through
`app/core/logging.py`: `time`, `level`, `logger`, `message`, `request_id` inside a request, and
the event's own fields. The API writes one `bodha.access` line per request with `method`, `route`
(the route template, such as `/api/notes/{note_id}`, or `unmatched`), `status`, `duration_ms` and
`request_id`; uvicorn's own access log is off. A request's `X-Request-ID` is kept when it is 16 to
64 hexadecimal characters or dashes, otherwise a new one is issued, and the response always
carries it.

The access line never carries query strings, raw paths, bodies, headers or client addresses, and
log messages name records by id only, never by email, name or token. Exceptions are logged by
type, the last 20 stack frames and the types of their causes;
their messages are not logged, because messages from the app and its libraries can carry file
names (which include patient names) or SQL parameters.

The worker writes a CloudWatch Embedded Metric Format line once a minute: namespace `BodhaCoder`,
metrics `QueuedAnalyses` (queued and due) and `RunningAnalyses`, no dimensions. CloudWatch Logs
turns these lines into metrics without an agent. Every worker task reports the same counts, so
alarms and scaling use the `Maximum` statistic.

## Local and staging with Docker Compose

`docker-compose.yml` runs Postgres 17, LocalStack (S3, SES and SNS), a one-shot `migrate`, `api`,
`worker` and `web`. Only `web` (`127.0.0.1:3000`) and LocalStack (`127.0.0.1:4566`) are published,
on the loopback address.

1. `copy .env.compose.example .env.compose` and fill in every key. `.env.compose` is ignored by git.

   | Key | Value |
   |---|---|
   | `POSTGRES_PASSWORD` | letters and digits only (it is placed in a URL) |
   | `SECRET_KEY` | `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
   | `MFA_ENCRYPTION_KEY` | `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
   | `GEMINI_API_KEY` | a key for test data only |
   | `LOCALSTACK_AUTH_TOKEN` | from a free LocalStack account; LocalStack requires one since its 2026.03 release |
   | `APP_URL`, `COOKIE_SECURE` | leave empty for `http://localhost:3000` and `true` |
   | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | empty unless testing Google sign-in |
   | `MICROSOFT_CLIENT_ID`, `MICROSOFT_CLIENT_SECRET`, `MICROSOFT_TENANT` | empty unless testing Microsoft sign-in; the tenant defaults to `common` |
   | `YAHOO_CLIENT_ID`, `YAHOO_CLIENT_SECRET` | empty unless testing Yahoo sign-in |
   | `BOOTSTRAP_HQ_EMAIL`, `BOOTSTRAP_HQ_PASSWORD` | the first HQ account |

2. `docker compose --env-file .env.compose up --build`
3. `docker compose --env-file .env.compose run --rm migrate python -m app.scripts.bootstrap_hq`
4. Open `http://localhost:3000`.

LocalStack's ready hook (`tools/localstack/init_aws.py`) creates the bucket (versioned, encrypted,
public access blocked) and the SES identity for `MAIL_FROM`; LocalStack reports healthy only after
the hook succeeds. The backend reaches LocalStack through `S3_ENDPOINT_URL` and `AWS_ENDPOINT_URL`
(boto3 sends SES and SNS calls there), both `http://localhost.localstack.cloud:4566`; inside the
network that name is an alias of the LocalStack container, and on the host it resolves to
`127.0.0.1`, so signed PDF links open in the browser. Sent emails are at
`http://localhost:4566/_aws/ses` and texts at `http://localhost:4566/_aws/sns/sms-messages`.

The compose stack is for test data only. LocalStack is not covered by any business associate
agreement, so real patient documents never go into it. For a shared staging host, put a TLS proxy
in front of `127.0.0.1:3000` and set `APP_URL` to its `https://` address.

## AWS reference deployment

Production is provisioned from `infra/tofu` with OpenTofu and released by `deploy.yml` from the
CHARTMATE-APP repository ([0025](decisions/0025-staging-on-aws.md), runbook in `infra/tofu/README.md`).

```
Internet ── ALB (HTTPS) ──┬── /api/*  ──> ECS service api    (uvicorn, port 8000)
                          └── default ──> ECS service web    (Next.js, port 3000) ──> api:8000
                                          ECS service worker (python -m app.worker)
api, worker ──> RDS for PostgreSQL 17 (Multi-AZ) · S3 (SSE-KMS) · SES · SNS
worker ──> Vertex AI (Gemini) through the NAT gateway
```

### Agreements

- **AWS**: accept the AWS Business Associate Addendum in AWS Artifact for every account that
  stores or processes PHI, and use only HIPAA eligible services. Everything below (VPC, ELB, ECS on
  Fargate, ECR, RDS, S3, KMS, Secrets Manager, CloudWatch, CloudTrail, SES, SNS and AWS End User
  Messaging SMS, AWS Backup, WAF) is on the list today; check the current list before go-live.
- **Google**: sign the Google Cloud BAA for the production project and run the worker with
  `GEMINI_BACKEND=vertex` ([0012](decisions/0012-vertex-ai.md)): Gemini on Vertex AI is a covered
  service, the Gemini Developer API (`GEMINI_API_KEY`) is not, so it is for test data only. Use a
  regional US `GOOGLE_CLOUD_LOCATION`, keep the project to covered services, turn off Vertex AI data
  caching and request the abuse-monitoring logging exemption for zero data retention. The worker's
  Google identity is a service account with `roles/aiplatform.user` on that project only.
- **Twilio**, if used instead of SNS, needs its own BAA review; messages carry links and codes,
  never patient details.
- Keep production and staging in separate AWS accounts and Google projects. Staging holds synthetic
  data only.

### Network

- One VPC across three Availability Zones: public subnets for the ALB and a NAT gateway per zone,
  private subnets for the tasks, isolated subnets for RDS.
- Security groups: ALB accepts 443 (and 80, redirected) from the internet; `web` accepts 3000 from
  the ALB; `api` accepts 8000 from the ALB and from `web`; RDS accepts 5432 from `api` and
  `worker` (the `migrate` task uses the worker's group).
- VPC endpoints keep AWS traffic private: S3 (gateway), and interface endpoints for ECR (api and
  dkr), CloudWatch Logs, Secrets Manager, KMS, STS, SES (`email`) and SNS. Vertex AI, Google
  sign-in and Twilio leave through the NAT gateway.

### Load balancer

- HTTPS listener with an ACM certificate and `ELBSecurityPolicy-TLS13-1-2-2021-06`; the HTTP
  listener only redirects to HTTPS. Set the listener's `Strict-Transport-Security` response header.
- Rules: `/api/*` to the `api` target group (health check `/api/health`), everything else to the
  `web` target group (health check `/sign-in`). The API is reached directly, so uploads do not pass
  through the Next.js proxy and its timeout.
- Idle timeout 120 seconds (large uploads), drop invalid header fields, desync mitigation
  `strictest`, deletion protection on.
- AWS WAF with the managed common, known-bad-inputs and IP reputation rule groups, and a
  rate-based rule on `/api/auth/*` in front of the app's own limits.
- ALB access logs record full request URLs, and the queue search sends what people type (often a
  patient name) in the query string. Either leave access logs off or send them to a bucket handled
  as PHI (SSE-KMS, restricted, same lifecycle as the documents).

### ECS on Fargate

One cluster with Container Insights on (scaling uses its `RunningTaskCount`).

| Service | Command | Size | Tasks | Notes |
|---|---|---|---|---|
| `api` | `api` | 1 vCPU, 2 GB | 2 to 6, two zones | target group port 8000; `WEB_CONCURRENCY=1`; scale on CPU 60% |
| `worker` | `worker` | 1 vCPU, 2 GB | 1 to 4 | no load balancer; container health check off; scales on the queue (below) |
| `web` | default | 0.5 vCPU, 1 GB | 2 to 4, two zones | target group port 3000; `BACKEND_URL=http://api:8000` |

- Service Connect publishes `api` as `api:8000` inside the namespace, which is what `web` uses.
- Task definitions: `awslogs` driver to one log group per service, `initProcessEnabled: true`,
  `stopTimeout` 30 seconds for `api` and `web` and 120 for `worker`. `api` and `worker` run with
  `readonlyRootFilesystem: true` and an ephemeral volume at `/tmp` (uploads are spooled there);
  `web` rewrites its route table at start and so keeps a writable root.
- Deployments: rolling with minimum healthy 100% and maximum 200%, and the deployment circuit
  breaker with rollback.
- ECS Exec stays off for `api` and `worker` in production; turn it on only for a recorded
  break-glass session, with session logging to an encrypted log group.
- The execution role pulls from ECR, writes the log groups, and reads exactly the secrets its task
  definition references (with `kms:Decrypt` on the secrets key).

| Task role | Allows |
|---|---|
| `api` | `s3:GetObject`, `s3:PutObject`, `s3:DeleteObject`, `s3:ListBucket` on the documents bucket; `kms:GenerateDataKey`, `kms:Decrypt` on its key; `ses:SendEmail` on the sending identity and configuration set; `sns:Publish` |
| `worker` | the same S3 and KMS actions, `ses:SendEmail`, `sns:Publish` |
| `migrate` | nothing beyond the database |
| `web` | nothing |

### Configuration

| Setting | `api` | `worker` | `migrate` | Source |
|---|---|---|---|---|
| `DATABASE_URL` (`postgresql+asyncpg://bodha_app:…@<endpoint>:5432/bodha?ssl=require`) | yes | yes | yes | secret |
| `SECRET_KEY` | yes | yes | yes | secret |
| `MFA_ENCRYPTION_KEY` | yes | | | secret |
| `GOOGLE_CLIENT_SECRET`, `MICROSOFT_CLIENT_SECRET`, `YAHOO_CLIENT_SECRET` | yes | | | secret |
| `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `PAYPAL_CLIENT_SECRET` | yes | yes | | secret |
| `STRIPE_PRICE_*` (four), `PAYPAL_CLIENT_ID`, `PAYPAL_WEBHOOK_ID`, `PAYPAL_ENVIRONMENT`, `PAYPAL_PLAN_*` (four), `BILLING_GRACE_DAYS` | yes | yes | | plain |
| `GOOGLE_CREDENTIALS_JSON` (the Vertex AI service account credential) | | yes | | secret |
| `GEMINI_BACKEND=vertex`, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION` | | yes | | plain |
| `APP_URL=https://www.bodhaai.co`, `COOKIE_SECURE=true`, `APP_ENVIRONMENT=production` | yes | yes | | plain |
| `GOOGLE_CLIENT_ID`, `MICROSOFT_CLIENT_ID`, `MICROSOFT_TENANT`, `YAHOO_CLIENT_ID` | yes | | | plain |
| `SELF_SIGNUP_ENABLED`, `TRIAL_DAYS`, `TRIAL_SEATS`, `TERMS_URL`, `BAA_URL`, `PRIVACY_URL`, `AGREEMENT_VERSION` | yes | | | plain |
| `S3_BUCKET`, `S3_REGION`, `S3_SERVER_SIDE_ENCRYPTION=` (empty) | yes | yes | | plain |
| `EMAIL_TRANSPORT=ses`, `SMS_TRANSPORT=sns`, `SNS_ORIGINATION_NUMBER`, `MAIL_FROM`, `AWS_MESSAGING_REGION`, `SES_CONFIGURATION_SET` | yes | yes | | plain |
| `GEMINI_MODEL`, `AI_WORKERS` | | yes | | plain |
| `FORWARDED_ALLOW_IPS=<VPC CIDR>`, `WEB_CONCURRENCY=1` | yes | | | plain |

`S3_SERVER_SIDE_ENCRYPTION` must be empty on AWS: the app then sends no encryption header and the
bucket's default SSE-KMS key applies. The default `AES256` would store objects under SSE-S3 instead,
and `aws:kms` without a key id would use the AWS managed key rather than the bucket's key. No
`S3_ENDPOINT_URL`, `AWS_ENDPOINT_URL` or access keys on AWS: the task role supplies credentials.
`ssl=require` encrypts the database connection; verifying the server certificate needs the RDS CA
bundle in the image.

### Self sign-up and sign-in services

Practices can start a trial on their own ([0026](decisions/0026-self-serve-sign-up.md)).

| Setting | Default | Meaning |
|---|---|---|
| `SELF_SIGNUP_ENABLED` | `true` | `false` answers 404 on `/api/signup` and hides "Start a free trial"; a sign-in service then refuses an email without an account |
| `TRIAL_DAYS` | `14` | the trial ends this many days after sign-up, in the practice's time zone |
| `TRIAL_SEATS` | `5` | seats of a new trial practice |
| `TERMS_URL` | empty | the terms of service, linked from the agreement checkbox |
| `BAA_URL` | empty | the business associate agreement; while empty, the checkbox reads "I will use test data only" |
| `PRIVACY_URL` | empty | the privacy policy, linked when set |
| `AGREEMENT_VERSION` | `unpublished` | stored with each acceptance in `practices.signup`; change it whenever the terms or the BAA change |

With `APP_ENVIRONMENT=production` and self sign-up on, the API refuses to start unless `BAA_URL` and
`TERMS_URL` are set. Set both, or `SELF_SIGNUP_ENABLED=false`, before this release reaches production.
Links must be `https://` (or `http://`) addresses.

A sign-in service is on only when both its client id and secret are set. Register
`{APP_URL}/api/auth/{provider}/callback` as the redirect URI of each:

| Environment | Google | Microsoft | Yahoo |
|---|---|---|---|
| Local | `http://localhost:3000/api/auth/google/callback` | `http://localhost:3000/api/auth/microsoft/callback` | https only: a TLS tunnel's address + `/api/auth/yahoo/callback` |
| Staging | `https://bodha-coder.vercel.app/api/auth/google/callback` | `https://bodha-coder.vercel.app/api/auth/microsoft/callback` | `https://bodha-coder.vercel.app/api/auth/yahoo/callback` |
| Production | `https://www.bodhaai.co/api/auth/google/callback` | `https://www.bodhaai.co/api/auth/microsoft/callback` | `https://www.bodhaai.co/api/auth/yahoo/callback` |

- Google: an OAuth client of type "Web application"; scopes `openid email profile`.
- Microsoft: an Entra ID app registration for "accounts in any organizational directory and personal
  Microsoft accounts" (`MICROSOFT_TENANT=common`; `organizations`, `consumers` or one tenant id narrow
  it), a client secret, and the optional ID token claims `email` and `xms_edov`. Without `xms_edov` only
  personal Microsoft accounts are trusted.
- Yahoo: an app with OpenID Connect permissions `openid`, `email` and `profile`.

### Plans and billing settings

Practices choose a plan and pay by card (Stripe) or PayPal on `/plan`
([0028](decisions/0028-subscription-billing.md)). A processor is offered only when its credentials and
all four of its price ids are set; with none set, `/plan` shows the plans without a way to pay and HQ
sets plans by hand as before.

| Setting | Default | Meaning |
|---|---|---|
| `STRIPE_SECRET_KEY` | empty | the restricted or secret API key (`sk_live_…`, `sk_test_…` in test mode) |
| `STRIPE_WEBHOOK_SECRET` | empty | the signing secret of the webhook endpoint (`whsec_…`) |
| `STRIPE_PORTAL_CONFIGURATION` | empty | the customer portal configuration for Bodha (`bpc_…`); needed when the Stripe account serves other products, so the portal shows only Bodha's plans and branding |
| `STRIPE_PRICE_ESSENTIALS_MONTHLY`, `STRIPE_PRICE_ESSENTIALS_ANNUAL`, `STRIPE_PRICE_PROFESSIONAL_MONTHLY`, `STRIPE_PRICE_PROFESSIONAL_ANNUAL` | empty | the Stripe price ids (`price_…`) |
| `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET` | empty | the REST app's credentials |
| `PAYPAL_WEBHOOK_ID` | empty | the id of the app's webhook, used to verify each event |
| `PAYPAL_ENVIRONMENT` | `sandbox` | `sandbox` (`api-m.sandbox.paypal.com`) or `live` (`api-m.paypal.com`) |
| `PAYPAL_PLAN_ESSENTIALS_MONTHLY`, `PAYPAL_PLAN_ESSENTIALS_ANNUAL`, `PAYPAL_PLAN_PROFESSIONAL_MONTHLY`, `PAYPAL_PLAN_PROFESSIONAL_ANNUAL` | empty | the PayPal billing plan ids (`P-…`) |
| `BILLING_GRACE_DAYS` | `7` | days of access after a failed payment (0 to 60) |

The worker needs the same billing settings as the API: it keeps each subscription's quantity equal to
the practice's active providers.

### Set up Stripe and PayPal

Amounts must match `backend/app/services/plans.py`; change both together. Do everything in Stripe test
mode and the PayPal sandbox first, run a checkout, a renewal (Stripe test clocks), a failed payment and
a cancellation, then repeat in live mode.

Stripe (Dashboard):

1. Products: create **Bodha Assure Essentials** and **Bodha Assure Professional**. On each, add two
   recurring prices in USD, per unit (the unit is one active provider), tax behaviour as your accountant
   advises: Essentials $149.00 monthly and $1,490.00 yearly; Professional $249.00 monthly and $2,490.00
   yearly. Copy the four `price_…` ids into `STRIPE_PRICE_*`.
2. Settings, Billing, Customer portal: turn on update payment method, view invoice history, cancel
   subscriptions (at the end of the billing period) and switch plans between the four prices above
   (quantity changes off: Bodha sets the quantity). Set the default return link to `{APP_URL}/plan`.
3. Settings, Billing, Subscriptions and emails: turn on Smart Retries and choose to mark the
   subscription unpaid or cancel it after the last retry; send failed-payment emails.
4. Developers, Webhooks: add the endpoint `{APP_URL}/api/billing-webhooks/stripe` (for example
   `https://www.bodhaai.co/api/billing-webhooks/stripe`) with exactly these events:
   `checkout.session.completed`, `customer.subscription.created`, `customer.subscription.updated`,
   `customer.subscription.deleted`, `invoice.paid`, `invoice.payment_failed`. Copy its signing secret
   into `STRIPE_WEBHOOK_SECRET`.
5. Developers, API keys: put the secret key (or a restricted key with write access to Checkout
   Sessions, Customer portal, Subscriptions and read access to Prices) in `STRIPE_SECRET_KEY`.

PayPal (developer.paypal.com):

1. Apps & Credentials (Sandbox, later Live): create a REST app; copy its client id and secret into
   `PAYPAL_CLIENT_ID` and `PAYPAL_CLIENT_SECRET`; leave `PAYPAL_ENVIRONMENT=sandbox` until going live.
2. Create two products (`POST /v1/catalogs/products`, type `SERVICE`) and four billing plans
   (`POST /v1/billing/plans`), each with one regular cycle (`total_cycles` 0), `quantity_supported`
   true, and a fixed price per unit in USD: Essentials 149.00 every 1 MONTH and 1490.00 every 1 YEAR;
   Professional 249.00 every 1 MONTH and 2490.00 every 1 YEAR; `payment_failure_threshold` 3. Copy the
   four `P-…` ids into `PAYPAL_PLAN_*`.
3. In the app, add the webhook `{APP_URL}/api/billing-webhooks/paypal` with these events:
   `BILLING.SUBSCRIPTION.ACTIVATED`, `BILLING.SUBSCRIPTION.RE-ACTIVATED`, `BILLING.SUBSCRIPTION.UPDATED`,
   `BILLING.SUBSCRIPTION.CANCELLED`, `BILLING.SUBSCRIPTION.SUSPENDED`, `BILLING.SUBSCRIPTION.EXPIRED`,
   `BILLING.SUBSCRIPTION.PAYMENT.FAILED`, `PAYMENT.SALE.COMPLETED`, `PAYMENT.SALE.DENIED`. Copy the
   webhook id into `PAYPAL_WEBHOOK_ID`.

Both: webhooks reach the API through the web server's `/api` proxy, which passes the body unchanged.
The local address (`http://localhost:3000`) is not reachable from the processors: use the Stripe CLI
(`stripe listen --forward-to localhost:3000/api/billing-webhooks/stripe`, which prints a `whsec_…` for
`STRIPE_WEBHOOK_SECRET`) or a TLS tunnel for PayPal. Nothing about a patient is ever sent: only the
admin's email, the practice id, the plan and the provider count.

### Database: RDS for PostgreSQL 17

- Multi-AZ deployment, Graviton general-purpose instance (`db.m7g.large` covers the target), gp3
  storage with autoscaling, storage and Performance Insights encrypted with a customer managed KMS
  key, deletion protection, `rds.force_ssl=1`, automatic minor version upgrades in the maintenance
  window.
- Automated backups kept 35 days, which gives point-in-time restore to any second in that window.
- The master user's password is managed by RDS in Secrets Manager and used only by people. The app
  connects as `bodha_app`, which owns the schema; its password lives in the `DATABASE_URL` secret.
- Parameter group: `log_parameter_max_length=0` and `log_parameter_max_length_on_error=0`, and no
  `log_statement=all`, so query parameters (patient data) never reach the database logs.
  `log_min_duration_statement=1000` is safe with those set.
- Each API process holds up to 15 connections and each worker task about `AI_WORKERS + 2`; the
  instance's default `max_connections` is far above the fleet at its maximum size.

### Object storage: S3

- One bucket per environment, Block Public Access on (all four settings), Object Ownership
  "bucket owner enforced", versioning on.
- Default encryption SSE-KMS with a customer managed key and S3 Bucket Keys.
- Bucket policy: deny any request without TLS (`aws:SecureTransport` false), and deny
  `s3:PutObject` whose `s3:x-amz-server-side-encryption` is `AES256`, so a wrong setting fails
  loudly.
- Lifecycle: abort incomplete multipart uploads after 7 days; move current objects to Standard-IA
  after 90 days; expire noncurrent versions 30 days after they become noncurrent; remove expired
  delete markers. Deleting a practice therefore leaves recoverable versions for 30 days.
- CloudTrail data events for the bucket (reads and writes) to a separate, locked log bucket.
- No CORS configuration is needed: signed PDF links are opened, not fetched.
- The worker deletes, once a day, objects older than 24 hours that no record holds (the orphan sweep in
  [ARCHITECTURE.md](ARCHITECTURE.md#records-replaced-pdfs-retention-and-practice-deletion)); it needs
  no permission beyond its task role's.
- Email intake adds the `ses-inbound/` prefix, an SES statement in this bucket policy and the key
  policy, a one-day lifecycle rule on that prefix and a Lambda function: [infra/ses_intake](../infra/ses_intake/README.md).

### Email: SES

- Verify the sending domain with Easy DKIM (2048-bit), a custom MAIL FROM subdomain so SPF aligns,
  and a DMARC record (`v=DMARC1; p=quarantine; rua=…`, moving to `p=reject` once reports are
  clean).
- Request production access to leave the sandbox before inviting real users.
- A configuration set (`SES_CONFIGURATION_SET`) with bounce and complaint events to an SNS topic or
  CloudWatch; keep the account-level suppression list on.
- Messages contain sign-in links and codes, never patient details.

### Text messages: SNS

- Register an origination identity in AWS End User Messaging SMS: a toll-free number with
  completed toll-free verification, or a 10DLC campaign, for US recipients. Set
  `SNS_ORIGINATION_NUMBER` to that number in E.164 form (`+18885550100`); every text is sent from it.
- Texts are offered only when they can be sent ([0030](decisions/0030-texts-only-when-set-up.md)):
  `SMS_TRANSPORT=sns` with `SNS_ORIGINATION_NUMBER`, or `twilio` with `TWILIO_ACCOUNT_SID`,
  `TWILIO_AUTH_TOKEN` and `TWILIO_FROM`, or any transport with `APP_ENVIRONMENT=development`. Otherwise
  the text choice is hidden, a request to text a provider answers 409, and a provider who prefers texts
  is sent email.
- Move the account out of the SMS sandbox, raise the monthly spend limit from its default, set the
  default message type to transactional, and keep opt-out handling on.

### Secrets: Secrets Manager

| Secret | Read by |
|---|---|
| `bodha/<env>/database-url` | api, worker, migrate |
| `bodha/<env>/secret-key` | api, worker, migrate |
| `bodha/<env>/mfa-encryption-key` | api |
| `bodha/<env>/google-client-secret` | api |
| `bodha/<env>/google-credentials` (Vertex AI service account) | worker, as `GOOGLE_CREDENTIALS_JSON` |
| `bodha/<env>/stripe` (`STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`) | api, worker |
| `bodha/<env>/paypal-client-secret` | api, worker |
| `bodha/<env>/bootstrap-hq` | the one-off bootstrap task, deleted afterwards |

Encrypt every secret with a customer managed key and inject them through the task definition's
`secrets` (`valueFrom` the secret ARN), never as plain environment values. Tasks read secrets at
start, so a changed secret takes effect on the next deployment. Rotating `SECRET_KEY` signs everyone
out; rotating `MFA_ENCRYPTION_KEY` follows its runbook. A service account key is rotated every 90
days (add the new key, store it, redeploy `worker`, delete the old key). Workload identity
federation removes the key, but Google's AWS credential source reads EC2 instance metadata, which
Fargate tasks do not have, so it needs a credential supplier the adapter does not provide.

### Logs, metrics and alarms: CloudWatch

- Log groups `/bodha/<env>/api`, `/worker`, `/web`, `/migrate`, encrypted with KMS, kept 400 days.
  The PHI access log lives in Postgres (`access_log`), kept for each practice's retention period.
- Metric filters: `{ $.logger = "bodha.access" && $.status >= 500 }` on the API group and
  `{ $.level = "ERROR" }` on the worker group.
- Alarms, all to one SNS topic for the on-call rota (alarm text names metrics, never data):

| Alarm | Condition |
|---|---|
| API 5xx rate | ALB `HTTPCode_Target_5XX_Count / RequestCount` for the `api` target group above 2% for 5 minutes |
| Unhealthy targets | `UnHealthyHostCount` above 0 for 5 minutes, per target group |
| Worker failures | worker `ERROR` lines: 3 or more in 15 minutes |
| Worker down | `RunningTaskCount` of `worker` below 1 for 3 minutes, or `QueuedAnalyses` missing for 5 minutes (missing data is breaching) |
| Queue age | `QueuedAnalyses` (Maximum) above 0 while `RunningAnalyses` is 0 for 10 minutes, or above 100 for 30 minutes |
| Database | `CPUUtilization` above 80%, `FreeStorageSpace` below 20%, `DatabaseConnections` above 80% of the limit |

### Worker autoscaling

Scale the `worker` service with target tracking on queued analyses per running task:

```json
{
  "TargetValue": 16,
  "CustomizedMetricSpecification": {
    "Metrics": [
      {"Id": "queued", "ReturnData": false,
       "MetricStat": {"Stat": "Maximum", "Metric": {"Namespace": "BodhaCoder", "MetricName": "QueuedAnalyses"}}},
      {"Id": "tasks", "ReturnData": false,
       "MetricStat": {"Stat": "Average", "Metric": {"Namespace": "ECS/ContainerInsights", "MetricName": "RunningTaskCount",
         "Dimensions": [{"Name": "ClusterName", "Value": "bodha-prod"}, {"Name": "ServiceName", "Value": "worker"}]}}},
      {"Id": "backlog", "Expression": "queued / tasks", "Label": "Queued analyses per worker task"}
    ]
  },
  "ScaleOutCooldown": 60,
  "ScaleInCooldown": 600
}
```

Sixteen is about a minute of work for one task with `AI_WORKERS=8`. Keep the minimum at one task:
the worker also expires provider requests, sends reminders and re-queues reads left by a stopped
task. Set the maximum so that `tasks × AI_WORKERS` stays inside the Vertex AI quota. Every periodic
job locks the rows it acts on (`FOR UPDATE SKIP LOCKED`, or a per-practice lock for the daily summary),
so several tasks never send the same reminder or summary. On SIGTERM a task hands its in-flight reads
back to the queue at once, without spending an attempt, so deploys do not delay notes.

### Releases: migrations first

1. CI is green on the commit.
2. Build both images, tag them with the commit SHA, push to ECR.
3. Register task definition revisions for `api`, `worker`, `web` and `migrate` with that tag.
4. Run the migration as a one-off task in the private subnets with the worker's security group:
   `aws ecs run-task --cluster bodha-prod --launch-type FARGATE --task-definition bodha-migrate:<rev> --network-configuration …`,
   then `aws ecs wait tasks-stopped` and check the container's `exitCode` is `0` with
   `aws ecs describe-tasks`. A non-zero exit stops the release.
5. Update `api`, `worker` and `web` to the new revisions and wait for `aws ecs wait services-stable`.
6. `curl -fsS https://www.bodhaai.co/api/health/ready`.

Old tasks keep serving while new ones start, so every migration must work with the code one
release back: add columns and tables first, remove them a release later. Roll back by redeploying
the previous task definition revisions; the schema is never downgraded automatically. The first HQ
account is created once with the same image and `python -m app.scripts.bootstrap_hq` as a one-off
task reading `bootstrap-hq`.

### Backups and the restore drill

- RDS: automated backups (35 days, point in time) plus an AWS Backup plan that copies a daily
  snapshot to a vault in a separate backup account and region, with Vault Lock and retention set
  by the records policy.
- S3: versioning and the lifecycle above; replicate the bucket to the backup account
  (SSE-KMS replication with the destination key) where the records policy requires a second copy.
- Every quarter, and after any change to the database setup, run a restore drill and record the
  result (restore time against the four-hour target, data loss against the five-minute target).
  The restored copy holds PHI, so it lives in an isolated recovery VPC in the production account,
  never in staging:
  1. Restore the production database to a point in time 15 minutes ago as a new instance.
  2. Run one `api` task in the recovery VPC with `DATABASE_URL` pointing at the restored instance
     and the production bucket (read access only).
  3. Check that `/api/health/ready` is ready, that row counts of `notes`, `analyses` and
     `access_log` match the source at that time, and that three random notes open with their PDFs.
  4. Delete the restored instance and the task, write the drill record, and fix whatever took
     longest.
