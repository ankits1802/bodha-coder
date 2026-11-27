# Operations

Runbooks for a Bodha Coder deployment on AWS as described in [DEPLOY.md](DEPLOY.md). Every action
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
| Readiness | `curl -fsS https://coder.example.com/api/health/ready` |

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
worker's security group and ECS Exec on, run `psql` with the `bodha_app` credentials from the
`database-url` secret, and stop the task when done.

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
no practice row and no `practice deleted` entry, left alone).

```
filter message = "orphan file sweep"
| fields @timestamp, deleted, kept, recent, intake, unknown, unknown_folders
| sort @timestamp desc
```

`unknown` or `unknown_folders` above zero means objects nothing in Bodha accounts for: list them with
`aws s3 ls --recursive s3://<bucket>/practices/<practice id>/` (keys hold ids only), find their source,
and delete them by hand only once that is understood. A deleted object stays recoverable for 30 days
as a noncurrent version (Restore from backup, Documents).

## Restore from backup

Decide first what was lost: a mistaken change in the database, deleted documents, or the whole
instance. Record the incident and start the breach assessment if PHI may have been exposed.

Database to a point in time:

1. RDS console, the instance, "Restore to point in time", a time just before the damage, as a new
   instance with the same parameter group, subnet group, security group and KMS key.
2. Scale `worker` to zero and put the app in maintenance (ALB fixed response on the HTTPS
   listener) so nothing writes to the old instance.
3. Update `bodha/<env>/database-url` to the new endpoint, run the `migrate` task (it should be a
   no-op), then redeploy `api` and `worker` and remove the maintenance rule.
4. Check readiness, then rename the instances so the restored one carries the production name;
   keep the old one stopped until the incident is closed, then delete it.

A partial repair (one practice's rows) is done by restoring to a separate instance and copying
only the affected rows back, reviewed by two people.

Documents: the bucket is versioned, so a deleted or overwritten PDF is recovered by deleting its
delete marker or copying the earlier version back, for 30 days:

```
aws s3api list-object-versions --bucket <bucket> --prefix practices/<practice id>/notes/<note id>/
aws s3api delete-object --bucket <bucket> --key <key> --version-id <delete marker version id>
```

## Purge a practice

When a practice leaves and its data must be deleted (end of contract, at the practice's written
request, after its records have been returned):

1. Export what the practice is owed first (approved codes, and the access log while its retention
   period runs) and record the handover.
2. In HQ, end or block the practice, then delete it and type its name to confirm. This deletes
   every row that belongs to the practice (its people, providers, notes and their history, provider
   requests and access log), records "practice deleted" in HQ activity, and deletes every object
   under `practices/<practice id>/`.
3. If the HQ log shows "stored files of deleted practice … were not removed", the daily orphan sweep
   deletes them once they are 24 hours old. To remove them at once, delete them by hand:
   `aws s3 rm s3://<bucket>/practices/<practice id>/ --recursive`.
4. Earlier object versions stay recoverable for 30 days and then expire. To remove them at once:

   ```
   aws s3api list-object-versions --bucket <bucket> --prefix practices/<practice id>/ \
     --query "{Objects: [Versions, DeleteMarkers][][].{Key: Key, VersionId: VersionId}}" --output json > versions.json
   aws s3api delete-objects --bucket <bucket> --delete file://versions.json
   ```

   (`delete-objects` takes up to 1,000 entries per call.)
5. Database backups keep the rows until they age out (35 days for point-in-time restore, longer for
   vault copies). Tell the practice the date by which every copy is gone, and record it.
