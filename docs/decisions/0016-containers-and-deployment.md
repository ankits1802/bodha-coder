# 0016 Containers, logs and the AWS reference deployment

Context: Bodha Coder needed images, a local stack with the AWS services it uses, structured logs
without PHI, health endpoints and a documented production layout on AWS.

## Choice

- One API image runs the API, the worker and migrations (`api`, `worker`, `migrate`), so the three
  can never run different code. Dependencies are installed from wheels only, as a non-root user,
  with no compiler in the final stage.
- The web image is built once and given `BACKEND_URL` at start. Next.js fixes rewrites at build
  time, so the build writes a placeholder and the start script replaces it in the files that
  contain it; the build fails if Next stops writing the rewrite to `routes-manifest.json`. A
  `proxy.ts` rewrite was rejected because it buffers request bodies up to a size limit, which large
  PDF uploads exceed.
- On AWS the load balancer sends `/api/*` straight to the API, so uploads skip the Next.js proxy
  and its timeout; the web service still proxies for local use.
- Logs are JSON lines on stdout, one access line per request with the route template only.
  Exception messages are never logged: upload errors name files, and file names carry patient
  names; SQL errors carry parameters. The type, frames and cause types are enough to find the code.
- Readiness checks the database and the bucket with two-second limits; liveness checks nothing
  else, so load balancers never restart tasks for a dependency outage.
- The local stack uses LocalStack for S3, SES and SNS. LocalStack shell hooks need a shebang, which
  the no-comment rule forbids, so the hook is Python (`tools/localstack/init_aws.py`), which
  LocalStack runs in its own interpreter.
- The load test uses k6: one static binary or image, arrival-rate scenarios that model notes per
  day directly, and thresholds that fail the run.

- Python dependencies (amended 2026-11-27): `backend/requirements.lock` pins every package,
  direct and transitive, for Linux images and Windows development in one file (`uv pip compile
  --universal --python-version 3.14`, without header or annotations, so it holds no comments). CI
  installs it as is (`pip install -r`) and the project with `--no-deps`; the image takes it as
  constraints over the runtime dependencies, so test tools stay out of the image. CI compiles it
  again with the committed file as preferences and fails on any difference: the lock no longer
  matches `pyproject.toml`. A new upstream release does not fail it; upgrades are a recompile
  with `--upgrade`. uv (0.13.10) only compiles; pip installs.

## Follows

- `tools/hygiene_check.py` checks Dockerfiles, `.dockerignore`, shell scripts and `.lock` files for comments.
- The worker reports queue metrics through `log_queue_metrics`, and the worker service scales on
  them ([0013](0013-postgres-job-queue-no-sqs.md)).
- Production sets `S3_SERVER_SIDE_ENCRYPTION` empty so the bucket's KMS key applies.
