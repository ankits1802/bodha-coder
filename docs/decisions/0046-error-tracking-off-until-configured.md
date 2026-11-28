# 0046 Error tracking with Sentry, off until configured

Date: 2026-11-28

Context: errors were visible only in CloudWatch logs (type, frames and causes, never messages). The owner
wants error tracking for the API, the worker and the web app, active only when a DSN is set, inert
otherwise, with nothing that could be patient data leaving Bodha. The Sentry projects do not exist yet.

## Choices

**Official SDKs, pinned.** `sentry-sdk` 3.0.1 for Python and `@sentry/nextjs` 11.20.0, the latest stable
releases. Both majors replaced `send_default_pii` with a `data_collection` option whose defaults collect
more than before; every category is set off explicitly (user, cookies, headers, bodies, query strings,
GraphQL, generative AI inputs and outputs, database query data, queues, stack-frame variables, source
lines). That is the meaning of "send_default_pii off" in these versions.

**One DSN per runtime.** `SENTRY_DSN` for the api and worker, `WEB_SENTRY_DSN` for the web server and
browser. Empty means the SDK is never initialised: Python returns before `sentry_sdk.init`, the web
server does not import the SDK, and the browser loads it only when the root layout hands it settings.

**A scrubber that rebuilds, not one that deletes.** `before_send` builds a new event from an allowlist:
exception types, modules and stack frames (file, function, line, in-app), release, environment, level
and ids. Exception messages and log templates become `[redacted]` unless they are in a short allowlist of
fixed texts with no values (`SAFE_MESSAGES` in `core/error_reports.py` and `lib/errorReports/scrub.ts`).
Request data, user, extra, contexts other than runtime and trace ids, and tags other than `process` are
dropped. Breadcrumbs keep type, category, level and time, never a message or data. A URL keeps its path
with every segment that holds a digit masked as `:id`; stack frame URLs lose their query.

**What is captured.** Python: ERROR log records through `LoggingIntegration` (uvicorn logs every
unhandled request error, the worker logs every failed loop), plus uncaught exceptions; no automatic
framework, database or HTTP client integrations. Next.js: `onRequestError` on the server, global error
handlers and the two error boundaries in the browser. No tracing, no profiling, no release-health
sessions, no client reports, no session replay; the browser keeps only the error-handling integrations.

**Release.** `APP_VERSION`, the image tag `release.sh` writes into every task definition. The web task
also gets `APP_ENVIRONMENT`.

**CSP.** With `WEB_SENTRY_DSN` set, `src/proxy.ts` adds the DSN's origin (for example
`https://o123.ingest.us.sentry.io`) to `connect-src` and nothing else; scripts still load only from
Bodha with the nonce. An origin that is not plain `https://host` is refused.

**Secrets.** OpenTofu takes `sentry_dsn` and `web_sentry_dsn` (empty by default) and stores each
non-empty one write-only in Secrets Manager as `bodha/staging/sentry-dsn` and
`bodha/staging/web-sentry-dsn`; the task definitions read them through `secrets`. A DSN is a public
client key (the browser receives it), so the variables are not marked sensitive, which lets OpenTofu
decide from their emptiness which secrets exist.

## Follows

- Sentry becomes a subprocessor the moment a DSN is set. It is not listed now. Before either DSN is set,
  the subprocessors page must list Sentry (Functional Software, Inc.) with what it receives, its version
  must be bumped, and customer administrators notified as the page promises (DEPLOY.md, Error tracking).
- A new fixed error text that is known to carry no value can be added to `SAFE_MESSAGES`; anything built
  from a value stays redacted.
- Source maps are not uploaded; browser frames point at minified chunks.
