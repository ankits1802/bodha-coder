# Infrastructure

OpenTofu 1.13.10. Account-specific values never enter the repository: each stack reads them from a
gitignored `*.auto.tfvars`, and the state bucket from a gitignored `backend.hcl`.

| Stack | Holds | State |
|---|---|---|
| `bootstrap` | the state bucket and the operator's `bodha-staging-edge` policy | `bootstrap/terraform.tfstate` in the state bucket |
| `envs/staging` | network, data, app, alarms and the GitHub deploy role | `staging/terraform.tfstate` |

## First run

1. `bootstrap/bootstrap.auto.tfvars`: `account_id`, `operator_user`. With a temporary
   `backend_override.tf` (`terraform { backend "local" {} }`): `tofu init`, `tofu apply`. Then delete
   the override, write `backend.hcl` (`bucket = "bodha-tofu-state-<account>"`) and run
   `tofu init -migrate-state -backend-config=backend.hcl`.
2. `envs/staging/staging.auto.tfvars`: `account_id`, `alert_email`, `hq_email`, optionally
   `mail_from_address`. `tofu init -backend-config=../../bootstrap/backend.hcl`, `tofu plan -out=review.tfplan`,
   review, `tofu apply review.tfplan`.
3. Copy the `deploy` output into the CHARTMATE-APP repository variables
   (`gh variable set NAME --body VALUE --repo CHARTMATE-APP/bodha-coder`); the next push to `main`
   releases.
4. Create the first HQ user once: run the `bodha-staging-bootstrap` task with the deploy subnets and
   security group; read the password with
   `aws secretsmanager get-secret-value --secret-id bodha/staging/bootstrap-hq`.

Rotate the database password by raising `database_password_version` and applying, then forcing a new
deployment of the three services.

## Frontend on Vercel

The Vercel CLI on an operator's machine may be signed in to another account. Keep this project's
login separate with a dedicated global-config folder outside the repository and pass it to every
command: `vercel login -Q <folder>`, `vercel -Q <folder> link --project bodha-coder` in `frontend/`,
`vercel -Q <folder> env add BACKEND_URL production`. Releases from CHARTMATE-APP use
`deploy-frontend.yml` with the `VERCEL_TOKEN` secret and the `VERCEL_ORG_ID` and `VERCEL_PROJECT_ID`
repository variables.

