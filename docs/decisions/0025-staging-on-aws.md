# 0025 Staging on AWS with OpenTofu

Date: 2026-11-27

## Decision

Staging runs in the ChartMate AWS account (us-east-1), alongside ChartMate's own resources, as option A of three
compared with the owner: the production design at its smallest size. Everything is OpenTofu 1.13 in
`infra/tofu` (hashicorp/aws 6.74.0, hashicorp/random 3.9.1, pinned with lock files).

| Part | Staging choice | Production difference |
|---|---|---|
| Network | two zones; tasks in public subnets with public IPs, inbound only from the load balancer; load balancer and database in private subnets; S3 gateway endpoint | tasks in private subnets behind a NAT per zone, interface endpoints |
| Front door | CloudFront default HTTPS address reaching an internal load balancer through a VPC origin, so the load balancer has no public address | ACM certificate on the owner's domain, WAF |
| Compute | ECS Fargate: `api` on demand, `worker` and `web` on Fargate Spot, one task each, 0.25 vCPU | autoscaling, on demand, two zones |
| Database | RDS PostgreSQL 17 `db.t4g.micro`, single zone, 7-day backups, TLS forced, query values kept out of logs | Multi-AZ `db.m7g.large`, 35 days, separate admin and app users |
| Secrets | generated during apply and written only to RDS and Secrets Manager as write-only values: never in plans or state | the same |
| Email | SES only when a verified sender is configured; otherwise the outbox | SES on the owner's domain |
| AI | `GEMINI_BACKEND=demo` (synthetic notes only) | Vertex AI under the Google BAA |

Releases come only from `CHARTMATE-APP/bodha-coder`: `deploy-staging.yml` assumes the
`bodha-staging-deploy` role through GitHub OIDC (trusted only for that repository's `staging`
environment, no stored AWS keys), pushes both images to ECR, runs migrations as a one-off task and
rolls out the services. OpenTofu owns task definitions for configuration; CI owns the image, so
services ignore task-definition drift. The public repository runs tests only.

The operator's IAM user lacked CloudFront, SES and Budgets actions; with the owner's approval the
bootstrap stack attaches a scoped `bodha-staging-edge` policy for exactly those.

## Cost

About $64 a month at list prices: internal load balancer about $18, Fargate about $17, three task
public IPv4 addresses about $11, database about $14, KMS, secrets and CloudWatch about $4;
CloudFront stays inside its free tier. The budget alert at $100 filters on the `Project` cost
allocation tag, which a billing administrator must activate.

## Amendment (2026-11-27): frontend on Vercel

Until there is a domain, staging's public address is `https://bodha-coder.vercel.app` (Vercel team
`chart-mate`, project `bodha-coder`). Next.js forwards `/api/*` to `BACKEND_URL`, set in Vercel to
the CloudFront address, so the browser stays on one origin and cookies, uploads and API calls need no
change; `APP_URL` follows the Vercel address for links and Google sign-in. `deploy-frontend.yml`
builds with the Vercel CLI in GitHub Actions and deploys the prebuilt output, from CHARTMATE-APP
only, once a `VERCEL_TOKEN` repository secret exists. The ECS `web` service stays as a fallback.

Staging only: a browser request reaches the API through Vercel, CloudFront and the load balancer,
so the API sees Vercel's addresses rather than each user's, which loosens per-address sign-in rate
limits; and real patient data through Vercel would need Vercel's HIPAA agreement.

## Amendment (2026-11-27): one environment, production

At the owner's direction there is no staging: this stack is production, under the owner's
agreements.

- `APP_ENVIRONMENT=production`. `TERMS_URL`, `PRIVACY_URL` and `BAA_URL` point to `/legal/*` on the
  public address, which production self sign-up requires.
- Database backups are kept 35 days; all three services run on demand Fargate.
- The root stack is `envs/production` with state at `production/terraform.tfstate`. The deploy role
  trusts the CHARTMATE-APP `production` environment and the workflow is `deploy.yml`.
- AWS names keep the `bodha-staging` prefix and secrets stay under `bodha/staging/`: renaming would
  rebuild the database, load balancer, image repositories and secrets for no functional gain.
- `bodhaai.co` stays on GoDaddy DNS. `www.bodhaai.co` is a CNAME to CloudFront with a DNS-validated
  ACM certificate, and GoDaddy forwards the apex to it. Mail goes out as `no-reply@bodhaai.co`
  through an SES domain identity with 2048-bit Easy DKIM and MAIL FROM `mail.bodhaai.co`, so both
  DKIM and SPF align with the domain's existing `p=reject` DMARC policy; the Microsoft 365 records
  stay as they are. Setting `domain_name` creates the certificate and identity and lists the records
  to add (`tofu output dns_records`); `domain_live = true`, once they validate, attaches the
  certificate and moves `APP_URL` and the sender to the domain, which retires Vercel for the live site:
  `deploy-frontend.yml` is gone, the web image takes the address from the `SITE_URL` repository
  variable, and Vercel keeps only previews.
- A Route 53 HTTPS health check from three regions on `/api/health/ready` alarms to the alerts
  topic after two failed minutes.
- The `Project` cost allocation tag is active, so the budget filter now counts.

Cost rises to about $80 a month: on demand `worker` and `web` add about $13 and the health check
about $2. Still open before real patient documents: Gemini on Vertex AI under the Google BAA (the
developer API key is not covered), a Multi-AZ database, and tasks in private subnets behind NAT.
