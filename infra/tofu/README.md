# Infrastructure

OpenTofu 1.13.10. Account-specific values never enter the repository: each stack reads them from a
gitignored `*.auto.tfvars`, and the state bucket from a gitignored `backend.hcl`.

| Stack | Holds | State |
|---|---|---|
| `bootstrap` | the state bucket and the operator's `bodha-staging-edge` policy | `bootstrap/terraform.tfstate` in the state bucket |
| `envs/production` | network, data, app, email intake, alarms, uptime check and the GitHub deploy role | `production/terraform.tfstate` |

`envs/production` is production, although AWS names keep the `bodha-staging` prefix
([0025](../../docs/decisions/0025-staging-on-aws.md)). What it builds, against the reference design:
[docs/DEPLOY.md](../../docs/DEPLOY.md#what-opentofu-builds-today); the system it runs:
[docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md#system-context).

| Module | Builds |
|---|---|
| `modules/network` | the VPC across two zones, public and private subnets, the S3 gateway endpoint, the security groups |
| `modules/data` | the data and signing KMS keys, the documents bucket with Object Lock, RDS, the secrets, the SES identities, the backup vault and plan, CloudTrail |
| `modules/app` | ECR, the task roles, task definitions, the ECS cluster and services, the internal load balancer, CloudFront and its certificates |
| `modules/intake` | the inbound mail bucket, the email intake function and the SES receipt rule set |
| `modules/watch` | the alerts topic, alarms, dashboard, budget and the Route 53 health check |
| `modules/deploy` | the GitHub OIDC provider and the deploy role |

## First run

1. `bootstrap/bootstrap.auto.tfvars`: `account_id`, `operator_user`. With a temporary
   `backend_override.tf` (`terraform { backend "local" {} }`): `tofu init`, `tofu apply`. Then delete
   the override, write `backend.hcl` (`bucket = "bodha-tofu-state-<account>"`) and run
   `tofu init -migrate-state -backend-config=backend.hcl`.
2. `envs/production/production.auto.tfvars`: `account_id`, `alert_email`, `hq_email`, optionally
   `mail_from_address` and `domain_name`. `tofu init -backend-config=../../bootstrap/backend.hcl`,
   `tofu plan -out=review.tfplan`, review, `tofu apply review.tfplan`.
3. Copy the `deploy` output into the CHARTMATE-APP repository variables
   (`gh variable set NAME --body VALUE --repo CHARTMATE-APP/bodha-coder`) and create its `production`
   environment; the next push to `main` releases.
4. Create the first HQ user once: run the `bodha-staging-bootstrap` task with the deploy subnets and
   security group; read the password with
   `aws secretsmanager get-secret-value --secret-id bodha/staging/bootstrap-hq`.

## Domain

1. Set `domain_name` (for example `bodhaai.co`) and apply. `tofu output dns_records` lists the
   certificate validation CNAME, the `www` CNAME to CloudFront, three DKIM CNAMEs and the MAIL FROM
   MX and TXT records. Add them at the DNS host, leaving existing mail records alone, and forward the
   apex to `https://www.<domain>`.
2. When `aws acm describe-certificate` reports `ISSUED` and `aws sesv2 get-email-identity` reports
   DKIM `SUCCESS`, set `domain_live = true` (the site) and `domain_mail_live = true` (the sender;
   it can follow later) and apply, then add
   `https://www.<domain>/api/auth/<provider>/callback` to each sign-in provider and force a new
   deployment.

## Billing

Follow "Set up Stripe and PayPal" in `docs/DEPLOY.md`, then put the keys in Secrets Manager before
naming any price, because a task cannot start while a secret it reads is empty:
`aws secretsmanager put-secret-value --secret-id bodha/staging/<name> --secret-string file://<file>`
for `stripe-secret-key`, `stripe-webhook-secret` and `paypal-client-secret`. Then set `billing` in
`production.auto.tfvars` (`stripe_prices` and `paypal_plans` keyed `essentials_monthly`,
`essentials_annual`, `professional_monthly`, `professional_annual`, plus `paypal_client_id`,
`paypal_webhook_id` and `paypal_environment`), apply and force a new deployment.

## Texts

Texts stay off until a registered toll-free number exists: request one in AWS End User Messaging
SMS (us-east-1), complete its toll-free verification, then set `sms_origination_number` (E.164,
for example `+18885550100`) and apply. That switches `SMS_TRANSPORT` to `sns`, passes the number and
grants `sns:Publish`; the app then offers texts again.

## HQ host

Set `admin_subdomain` (for example `admin`) and apply: a certificate for both hosts is created and
`tofu output dns_records` adds its validation CNAME and the `admin` CNAME to CloudFront. When that
certificate is `ISSUED`, set `admin_live = true` and apply; CloudFront then answers for both hosts
with it, `ADMIN_URL` reaches the api, worker and web tasks, and a release (or forced deployment)
puts it in effect. Register `https://admin.<domain>/api/auth/<provider>/callback` with each sign-in
provider, then invite owners with a one-off task running
`python -m app.scripts.invite_hq "Full Name <email>" ...` on the worker task definition, whose role may send email (the migrate and bootstrap roles may not). A re-run of `deploy.yml` for a commit whose images exist skips the builds and only releases.

## Runtime database role

The api and worker connect as `bodha_runtime`, a role without DELETE on retained tables, no TRUNCATE
and no schema rights; migrations connect as the master `bodha_app` through `MIGRATION_DATABASE_URL`.
The migration that creates the role reads `RUNTIME_DATABASE_PASSWORD`, which only the migrate task
receives. First rollout: apply with `runtime_database = false`, release the migration, then set
`runtime_database = true`, apply and force a new deployment. Rotate by raising
`runtime_password_version`, applying, running `python -m app.scripts.runtime_password` once on the
migrate task definition (it alters the role to the new password), then forcing a new deployment.

## Retention

Everything is kept at least `retention_days` (2557, seven years; the variable refuses less):
document versions under S3 Object Lock in governance mode (old versions move to Glacier Instant
Retrieval after 90 days), monthly database snapshots in the `records` backup vault whose lock refuses
shorter retention, CloudWatch log groups, and a CloudTrail trail with log file validation and S3 data
events for the documents bucket, written to its own Object Lock bucket. Governance mode lets a role
with `s3:BypassGovernanceRetention` or `backup:DeleteBackupVaultLockConfiguration` act in a documented
emergency (misfiled PHI, a court order); the application roles have neither.

Rotate the database password by raising `database_password_version` and applying, then forcing a new
deployment of the three services.

## Email intake

Practices email visit notes to their own address at a subdomain
([0046](../../docs/decisions/0046-email-intake.md), [DEPLOY-INTAKE.md](../../docs/DEPLOY-INTAKE.md#option-3-email-to-the-practices-own-address)).
The apex domain's mail records (Microsoft 365) are not touched.

1. Apply `bootstrap` once more: the operator's `bodha-staging-edge` policy gains the SES receipt-rule
   actions (on `*`, as SES offers no resource-level permissions for them) and the Lambda actions on
   `function:bodha-*`.
2. Set `email_intake_subdomain = "intake"` and apply. This builds the function `bodha-staging-ses-intake`
   from `infra/ses_intake/handler.py`, its log group (2557 days), its role, the SES receipt role, the rule
   set `bodha-staging-intake` with its one rule, and the permission for SES to invoke the function. The
   rule set is not active yet, and the app still answers that email intake is unavailable. If the first
   apply stops at the receipt rule with "Could not write to bucket", the new role had not propagated:
   apply again.
3. Add the record `tofu output dns_records` now lists at GoDaddy, in the `bodhaai.co` zone:
   type `MX`, host `intake`, points to `inbound-smtp.us-east-1.amazonaws.com`, priority `10`, TTL one
   hour. Leave every other record as it is. `nslookup -type=mx intake.bodhaai.co` should answer it.
4. Run `aws ses describe-active-receipt-rule-set --region us-east-1`. Only one receipt rule set can be
   active per account and region, and this account is shared: if it names a rule set other than
   `bodha-staging-intake`, stop and ask the owner, because activating ours would switch that one off.
5. With nothing else active, set `email_intake_live = true`, apply and force a new deployment of `api`
   and `worker`: the rule set becomes active and `EMAIL_INTAKE_DOMAIN=intake.bodhaai.co` reaches both.
   An admin can then get an address and Send a test (Settings, Setup, Automatic intake).

To stop receiving, set `email_intake_live = false` and apply (the rule set is deactivated and the app
stops offering addresses; addresses and records stay), then remove the MX record.

## Error tracking

Set `sentry_dsn` (the Python project) and `web_sentry_dsn` (the Next.js project) and apply, after the
legal step in `docs/DEPLOY.md` (Error tracking). Each non-empty DSN is stored write-only as
`bodha/staging/sentry-dsn` or `bodha/staging/web-sentry-dsn` and read by the task definitions; empty
means no secret and no SDK. Force a new deployment afterwards.
