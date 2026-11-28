# Operations

Runbooks for a Bodha Assure deployment on AWS as described in [DEPLOY.md](DEPLOY.md). Every action
that touches PHI is done through the app where possible, so it lands in the access log. When a
runbook needs SQL, select ids, statuses and times only, never names, text or documents, and note the
session in the incident record.

## Where to look

| What | Where |
|---|---|
| API requests | log group `/bodha/<env>/api`, logger `bodha.access` |
| Worker | log group `/bodha/<env>/worker` |
| Queue | metrics `BodhaCoder/QueuedAnalyses` and `BodhaCoder/RunningAnalyses` (statistic Maximum) |
| Load balancer | ALB metrics per target group: `HTTPCode_Target_5XX_Count`, `TargetResponseTime`, `UnHealthyHostCount` |
| Readiness | `curl -fsS https://www.bodhaai.co/api/health/ready` |
| Email intake function | log group `/aws/lambda/bodha-<env>-ses-intake`, one `ses intake` line per message (message id and recipient count) |
| Email intake outcomes | each practice's Settings, Setup, Automatic intake, Received; `intake_messages` for SQL |
| Error tracking | the Sentry projects, when `SENTRY_DSN` and `WEB_SENTRY_DSN` are set ([DEPLOY.md](DEPLOY.md#error-tracking-sentry)); events carry the release (`APP_VERSION`) and exception types and frames only |

CloudWatch Logs Insights:

```
fields @timestamp, level, logger, message, route, status, duration_ms
| filter request_id = "<id from the X-Request-ID response header>"
| sort @timestamp
```

```
filter logger = "bodha.access"
| stats count() as requests, sum(status >= 500) as errors, pct(duration_ms, 95) as p95 by route
| sort errors desc
```

```
filter level = "ERROR"
| fields @timestamp, logger, message, error.type, error.causes.0
| sort @timestamp desc
```

For SQL, start a break-glass task from `postgres:17.12-trixie` in the private subnets with the
worker's security group and ECS Exec on, run `psql` with the `bodha_runtime` credentials from the
`database-url` secret, and stop the task when done. Use the schema owner (`migration-database-url`)
only for the maintenance runbook below.

## Production canary

`.github/workflows/canary.yml` runs every night at 08:17 UTC (and from Actions, production canary, Run
workflow) in `CHARTMATE-APP/bodha-coder` only, in the `production` environment. It checks
`/api/health/ready` on both hosts, signs in on `https://www.bodhaai.co` and `https://admin.bodhaai.co`
as two canary accounts, and opens Today, Insights, the Settings tabs, Account and Help, then the HQ
overview, practices, organizations, activity, spend, team and demo requests. It sends no request that
changes anything beyond signing in, and fails if the app tries to ([0049](decisions/0049-browser-journeys-and-production-canary.md)).
A failed run fails the workflow, and GitHub emails it to whoever last changed the schedule; keep Actions
failure emails on for that account. It keeps no trace or screenshot, so read the step that failed in
the run log. CI rehearses the same walk against its own stack on every run, so a failure at night
points at production or the canary accounts rather than the script.

### Set it up after merge

1. **Practice canary.** In HQ, Practices, Add practice: name `Bodha Canary`, plan Professional, a
   few seats, admin `Bodha Canary` with an address you read, for example `canary-practice@bodhaai.co`.
   A practice HQ adds has no renewal date, so its plan never ends; keep it so. Never add providers,
   upload notes, invite anyone or take payments in it, so its Today stays empty and opening it reads no
   patient record.
2. Open the invitation, set a long generated password, and at "Set up two-step verification" copy the
   **Setup key** (32 characters; drop the spaces). Add it to an authenticator too, enter the code, and
   keep the recovery codes in the owner's password manager. When the tour opens, Skip it, so the canary
   never meets it.
3. **HQ canary.** In HQ, Team, invite `Bodha Canary <canary-hq@bodhaai.co>` (or
   `python -m app.scripts.invite_hq "Bodha Canary <canary-hq@bodhaai.co>"`). Set its password on the
   admin host, copy its Setup key the same way, keep its recovery codes, and Skip the tour. HQ has one
   role, so this account can do anything HQ can: its secrets are owner credentials.
4. **GitHub.** In `CHARTMATE-APP/bodha-coder`, Settings, Environments, `production`, add the secrets:

   | Secret | Value |
   |---|---|
   | `CANARY_PRACTICE_EMAIL` | the practice canary's email |
   | `CANARY_PRACTICE_PASSWORD` | its password |
   | `CANARY_PRACTICE_TOTP_SECRET` | its Setup key, without spaces |
   | `CANARY_HQ_EMAIL` | the HQ canary's email |
   | `CANARY_HQ_PASSWORD` | its password |
   | `CANARY_HQ_TOTP_SECRET` | its Setup key, without spaces |

   Optional environment variables `CANARY_SITE_URL` and `CANARY_ADMIN_URL` point it at other hosts
   (defaults `https://www.bodhaai.co` and `https://admin.bodhaai.co`). The environment must let the
   default branch deploy, and it must not require a reviewer, or every night's run waits for one.
5. Run it once from Actions and check that both sign-ins pass.

### When it fails

- **Readiness**: follow "Where to look"; the readiness answer names the failing check (database or
  storage).
- **Sign-in**: "Email or password is not correct" means a secret is stale or the account was blocked;
  a refused code means the Setup key secret is wrong or two-step was reset (copy the new key). Two runs
  within the same 30 seconds share a code and the second is refused; run it again.
- **A page heading** that never shows: open that page as the canary and read the error.
- **"refused"** in the failure lists a request the app tried to send on its own (for example a tour
  that opened after a new tour version): sign in as that canary once by hand, Skip the tour, and run it
  again.

Each run writes only what a sign-in writes: rate-limit rows, a `signed_in` event per account with its
access-log or activity mirror, a session, and the last-active and last-code stamps.

## Gemini is out of credits or over quota

Symptoms: notes land in Failed with "The Gemini account has no credits left (HTTP 402)." (no retry)
or "Gemini … failed after retries (…)" (quota or outage: tried `AI_MAX_ATTEMPTS` times, 30 seconds
and 2 minutes apart, then failed); worker `ERROR` lines; `QueuedAnalyses` climbing while `RunningAnalyses`
stays at `AI_WORKERS` per task.

1. In the Google Cloud console for the production project, check billing (credits, budget, payment
   method) and Vertex AI quotas for the model in `GEMINI_MODEL` (requests and tokens per minute).
2. Restore credits, or raise the quota. Until then, lower `AI_WORKERS` or the worker maximum so
   retries do not burn the remaining quota.
3. When calls succeed again, notes that were still queued are read on their own. Failed notes are
   retried from each practice's queue (the Failed filter, then Retry), which records who retried
   them. Tell affected practices through HQ.

## Demo model backend

`GEMINI_BACKEND=demo` makes the worker answer every review with canned findings instead of calling
Gemini (model `bodha-demo`, zero tokens), so the whole flow runs on synthetic notes without credits.
The outcome of a note (matches, billed too high, billed too low, CDI query, audit risk) follows from
the SHA-256 of its PDF, or of its text when the PDF has a text layer; a note that carries a signed
addendum reads as matching. The API and the worker refuse to start with it when `APP_ENVIRONMENT` is
`production`, which is also the value when `APP_ENVIRONMENT` is not set. Never set it on a
deployment that holds real patient documents: its findings are not a review.

## Notes stuck queued

Symptoms: `QueuedAnalyses` above zero and not falling, the queue-age alarm, notes showing as
queued for more than a few minutes.

1. Check the worker service: running count, recent stops (`aws ecs describe-services`), and its
   last log lines. A task that stops at start usually lacks a secret or cannot reach the database.
2. If `RunningAnalyses` is zero and the worker is running, look for repeated `ERROR` lines: a
   database outage or a Vertex AI outage stops reads; follow the RDS console or the Gemini runbook.
3. Check whether the queue is only waiting: a read that failed for a transient reason is queued
   again 30 seconds, 2 minutes or 10 minutes later, and those are not counted until due.

   ```
   select status, count(*), min(requested_at), max(attempts)
   from analyses where status in ('queued', 'running') group by status;
   ```

4. Restart the worker with `aws ecs update-service --cluster bodha-prod --service worker --force-new-deployment`.
   Raise the worker maximum if the backlog is real demand and the Vertex AI quota allows it.

## Notes stuck reading

Symptoms: notes show "reading" for longer than `AI_JOB_TIMEOUT_SECONDS` (10 minutes by default).

1. A read is cut off after `AI_JOB_TIMEOUT_SECONDS` and retried. A worker that is stopped normally
   (SIGTERM, a deploy) hands its reads back to the queue immediately. A read whose worker died is
   found by the recovery loop once it has run for twice the timeout, and queued again (or failed
   after `AI_MAX_ATTEMPTS`). Waiting 20 minutes usually resolves it.
2. If it does not, the recovery loop is not running: check that at least one worker task is up and
   logging.

   ```
   select id, note_id, attempts, started_at from analyses
   where status = 'running' and started_at < now() - interval '20 minutes';
   ```

3. A note marked reading with no queued or running analysis is an inconsistency: set it to failed
   (`update notes set status = 'failed' where id = '<note id>' and status = 'reading'`) so the
   practice can retry it, and open a defect with the note id.

## Rotate MFA_ENCRYPTION_KEY

`MFA_ENCRYPTION_KEY` takes a comma-separated list. The first key encrypts; every listed key can
decrypt. Each secret is re-encrypted with the first key after the person's next good code, so the key
rotates without an outage.

1. Generate a key: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.
2. Store `<new key>,<old key>` as a new version of `bodha/<env>/mfa-encryption-key` and redeploy `api`.
3. Wait until everyone with two-step has signed in once (the access log shows sign-ins); anyone who has
   not can have two-step reset by their admin.
4. Store `<new key>` alone and redeploy. If the old key may have been exposed, skip the wait: store the
   new key alone at once and have admins reset two-step for everyone.

## Stored files without records

The worker's daily orphan sweep writes one `orphan file sweep` line to the worker log with counts only:
`deleted`, `kept`, `recent` (younger than 24 hours), `intake` (left in the inbox folders), `unknown`
(a key of a shape the sweep does not know, left alone) and `unknown_folders` (a practice folder with
no practice row, left alone). It deletes only objects whose owner row does not exist (a note, a
remittance or an evaluation run), such as an upload whose database transaction failed, or what a purge
failed to remove.

```
filter message = "orphan file sweep"
| fields @timestamp, deleted, kept, recent, intake, unknown, unknown_folders
| sort @timestamp desc
```

`unknown` or `unknown_folders` above zero means objects nothing in Bodha accounts for: list them with
`aws s3 ls --recursive s3://<bucket>/practices/<practice id>/` (keys hold ids only) and find their source.
Do not delete them by hand while they may belong to a record; Object Lock keeps every version for seven
years in any case.

## Email intake: a message did not arrive

Work from the outside in. Never open a stored message to find out: the records say what happened.

1. DNS: `nslookup -type=mx intake.bodhaai.co` must answer `10 inbound-smtp.us-east-1.amazonaws.com`.
2. SES: `aws ses describe-active-receipt-rule-set --region us-east-1` must name `bodha-staging-intake`
   with its rule enabled. If another rule set is active, someone activated it; do not switch it back
   without the owner.
3. Storage: `aws s3 ls s3://<bucket>/ses-inbound/` lists messages not yet handled. A message without its
   `.json` envelope means the function did not run or failed: read its log group (and the function's
   errors metric). An envelope that stays more than a few minutes means the worker failed on it: search
   the worker log for `email intake message <message id> failed`; the worker retries it every minute.
   `AMAZON_SES_SETUP_NOTIFICATION` is the test object SES writes when the rule is created and stays.
4. Worker: `EMAIL_INTAKE_DOMAIN` must be set on the worker task, or it skips email intake.
5. Records: the message's row in Received (or, for an address no practice holds, in SQL) gives the
   outcome and reason:

   ```
   select message_key, practice_id, outcome, reason, accepted_files, refused_files, created_at
   from intake_messages where created_at > now() - interval '1 day' order by created_at desc;
   ```

   `not_authenticated` means the sender's domain did not pass DMARC (or has no DMARC record);
   `sender_not_allowed` that the practice has not allowed that address or domain; `files_refused` that no
   PDF could be placed from page 1 (the file reasons say why).

A practice whose address may have leaked chooses New address; mail to the old one is then refused and
recorded. Raw messages stay under `ses-retained/` for seven years like every stored document.

## Restore from backup

Decide first what was lost: a mistaken change in the database, deleted documents, or the whole
instance. Record the incident and start the breach assessment if PHI may have been exposed.

Database to a point in time:

1. RDS console, the instance, "Restore to point in time", a time just before the damage, as a new
   instance with the same parameter group, subnet group, security group and KMS key.
2. Scale `worker` to zero and put the app in maintenance (ALB fixed response on the HTTPS
   listener) so nothing writes to the old instance.
3. Update `bodha/<env>/database-url` and `bodha/<env>/migration-database-url` to the new endpoint (the
   restored instance keeps both roles), run the `migrate` task (it should be a
   no-op), then redeploy `api` and `worker` and remove the maintenance rule.
4. Check readiness, then rename the instances so the restored one carries the production name;
   keep the old one stopped until the incident is closed, then delete it.

A partial repair (one practice's rows) is done by restoring to a separate instance and copying
only the affected rows back, reviewed by two people.

Documents: the bucket is versioned and under Object Lock, so a deleted or overwritten PDF is
recovered by deleting its delete marker or copying the earlier version back, for seven years:

```
aws s3api list-object-versions --bucket <bucket> --prefix practices/<practice id>/notes/<note id>/
aws s3api delete-object --bucket <bucket> --key <key> --version-id <delete marker version id>
```

## Close and purge a practice

Records are kept at least seven years from creation and seven years after a practice closes
([0038](decisions/0038-seven-year-retention-and-tamper-evidence.md)). A practice that leaves is closed,
not deleted; its records are purged only once that period has passed.

1. Export what the practice is owed first (approved codes, and the access log from Security, which is
   itself logged) and record the handover.
2. In HQ, end or block the practice, cancel any live subscription, then Close it and type its name. Every
   user is signed out, open provider requests are cancelled, queued reads stop, and HQ activity records
   `practice closed`. Nothing is deleted; HQ shows the date after which it may be purged
   (`closed_at` + `RETENTION_DAYS`, at least 2557 days).
3. After that date, and only if no legal hold, audit or investigation needs the records, Purge it in HQ
   and type its name. Bodha writes the practice's access log, with its chain columns, to
   `archives/practices/<practice id>/access-log.csv`, deletes the practice's rows (the practice row stays
   as `purged`, HQ activity stays), records `practice purged` with the rows removed and the archive's
   entry count and SHA-256, and deletes the objects under `practices/<practice id>/`. Postgres refuses the
   purge before 2557 days whatever the request says.
4. If the worker log shows "stored files of purged practice … were not removed", the next orphan sweep
   deletes them once they are 24 hours old.
5. Object versions stay until their seven-year Object Lock retention and the lifecycle rule end them;
   monthly backups taken while the practice was open age out seven years after each was taken. Tell the
   practice the date by which every copy is gone, and record it.

## Verify the audit log

The access log (one chain per practice) and HQ activity (one chain) are hash-chained by Postgres.

1. In HQ, Activity, choose Verify audit log (`POST /api/hq/audit-log/verify`). Each run is itself recorded
   as `audit log verified` with its result, which leaves a dated checkpoint in the activity chain.
2. Every chain intact: nothing to do. Keep the head sequence and hash if an auditor asks for a checkpoint
   outside Bodha.
3. A broken chain names the practice (or HQ activity), the first entry number and the problem:
   `missing rows` (an entry was removed), `broken link` (an entry's link does not match the one before) or
   `changed row` (an entry's content no longer matches its hash). Treat it as a security incident: do not
   change anything, record the result, compare with the latest backup taken before the reported entry
   (restore it to a separate instance and run `select * from bodha_verify_audit_log()` there), and review
   CloudTrail and the database logs for who connected as the schema owner. The runtime role cannot change
   or delete these rows, so a break means the schema owner, a superuser or a restore did.

## Change protected rows

Append-only tables, written-once columns, closed practices and every retained row are guarded by
triggers. A correction that truly needs one (for example a migration's data fix) is done only by the
schema owner, reviewed by two people and recorded in the incident or change record:

```
begin;
set local bodha.maintenance = 'on';
update ...;
commit;
```

The setting is ignored for any role that does not own the tables, so `bodha_runtime` cannot use it. A
change to `access_log` or `activity` breaks their hash chain at that entry, which the next verification
reports; record why beforehand.
