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
