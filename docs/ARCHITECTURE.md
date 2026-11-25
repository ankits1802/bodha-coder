# Architecture

## Processes

| Process | Command | Does |
|---|---|---|
| API | `uvicorn app.main:app` | authentication, tenants, uploads, review actions, provider links, exports |
| Worker | `python -m app.worker` | claims queued analyses (`FOR UPDATE SKIP LOCKED`), runs the review, stores results |
| Web | `next start` | the web client; proxies `/api` to the API |

Both Python processes share Postgres and the object store. The worker runs `AI_WORKERS` loops, a
recovery loop that re-queues analyses left running by a stopped worker, and a reminder loop every five
minutes: provider requests past their link expiry become `expired` (the note returns to its lane and a
held claim is released), and unanswered requests get at most two reminders, at 12 and 36 hours, each
with a fresh link.

## Data model and revisions

Nothing a person or the model produced is overwritten.

| Table | Holds | Revisions |
|---|---|---|
| `notes` | one visit document: file, patient, date of service, provider, place, lane, headline | current state only; everything below is the history |
| `note_texts` | the note's text: revision 1 from the document, then one per signed addendum | append-only |
| `analyses` | one row per model run or re-derivation: inputs (context), model, prompt version, tokens, validated report, raw response key | append-only; older runs become `superseded` |
| `suggestions` | each suggestion of an analysis: kind, codes before and after, action, reasoning, evidence quotes, severity, detail | belong to one analysis |
| `decisions` | each choice a person made on a suggestion | append-only; the latest per key applies |
| `code_sets` | billed and final code lists | append-only revisions per kind |
| `addendum_requests` | questions sent to a provider, the answers and the signed addendum | one per request |
| `access_log` | every PHI read, change and export (who, what, when, from where) | append-only |
| `activity` | administrative changes (setup, team, MIPS list, HQ) | append-only |
| `recovery_codes` | hashed single-use two-step recovery codes per user | replaced as a set |
| `rate_events` | one row per counted attempt (bucket, hashed key, time) | deleted once outside the window |

The models declare no ORM relationships, so a flush does not order inserts by foreign key and ids
are assigned at flush: flush a new row before adding rows that reference it.

The queued `analyses` row is the job. The worker records `attempts`, `error` and timing on it.

## Object storage (S3 or R2)

| Key | Content |
|---|---|
| `practices/{practice}/notes/{note}/document.pdf` | the uploaded PDF |
| `practices/{practice}/notes/{note}/analyses/{revision}.json` | every raw model reply of that analysis |

Keys carry ids only, never names. PDFs are opened through signed links that expire after
`PDF_LINK_SECONDS`.

## How a note flows

1. `POST /api/uploads` validates every file first (PDF signature, size, billed codes), stores
   the PDFs, and creates a batch, notes, billed code set revision 1 and a queued analysis each.
2. The worker claims the analysis, takes the latest note text (or extracts the PDF text, or
   sends the PDF itself when it has no text layer), and calls `ai.review.review_note` with the
   practice's enabled checks, the setting from the place of service, the billed codes and the
   practice MIPS scope.
3. `services.findings.build_findings` turns the report into suggestions. Every suggested ICD-10-CM
   code must be billable in the release for the date of service; every CPT code must be on the CMS
   fee schedule list or an E/M family; every modifier must be in the allowed set for its code;
   otherwise the suggestion is marked for review.
4. `services.routing.place` chooses the lane: compliance (flagged, a Critical audit risk, or the
   visit level two or more levels too high and not cleared), waiting on the provider, needs a coder
   (any code change), questions to send, or ready to approve. When the billed list has no ICD-10-CM
   code (`billed_diagnoses=False`), documented supported diagnoses join the claim without counting as
   code changes.
5. People decide. The claim is always derived: billed codes plus the latest decision on each
   suggestion. Approval writes a final code set revision.
6. Asking the provider stores the questions and emails or texts a link whose token travels in the
   URL fragment. The provider confirms a one-time code sent to the contact on file, answers, and
   signs; the answers become a new note text revision and a new analysis is queued.

## Modifiers, add-on codes and risk adjustment

| Piece | Flow |
|---|---|
| Modifiers | The E/M answer names each modifier and its code. `services.code_additions` keeps those in `codes/modifiers.py` (visit or procedure set) for a code on the claim as a `modifier` suggestion (`add`, code before to code with modifier); a visit modifier follows the suggested level. Others become `review` suggestions. `routing.claim` appends accepted modifiers to the claim's E/M code or to the named code |
| Add-on codes | Each add-on the E/M answer names becomes a `code_review` suggestion (`add`, `addon:<code>`) when `is_known_cpt` accepts it and it is not billed; otherwise `review`. Accepted ones are added to the claim once |
| Risk adjustment | With the `hcc` check, the model lists suspected conditions only. `codes/hcc.py` loads the vendored CMS-HCC V28 files for the payment year (date of service year + 1), maps billed and documented ICD-10-CM codes to payment HCCs with the CMS age and sex edits and hierarchies, and scores both sets from the CMS relative factors. `services.risk_adjustment` stores the result as one `diagnosis` suggestion with key `hcc` (action `info`) and each new suspected condition as a `diagnosis` question (`hcc:<code>`, `ask`) |
| MIPS status | Each eligible measure carries `met`, `missing` or `not_applicable`; the suggestion detail holds it |

Decision: [0010](decisions/0010-modifiers-add-ons-and-hcc.md).

## Calendar days

Each practice has a time zone (HQ sets it). Due dates (the end of the day of service plus the
turnaround), the addendum date, insights per day, recent batches and the access-log day are all
computed in that zone through `app/core/calendar.py`. Instants are stored and sent in UTC.

## Lanes

`notes.lane` is the worklist, `notes.lane_reason` says why in a fixed vocabulary (`flagged`,
`levels_too_high`, `audit_risk`, `waiting_on_provider`, `code_changes`, `questions`, `matches`), and
`notes.headline` is the sentence people read. Screens sort and filter on the reason, never the
headline.

## Security

Access tokens live in memory and carry a version; blocking, a role change, a password set or a
two-step reset bumps the version and revokes refresh sessions. Refresh tokens rotate on every use,
are stored hashed, and expire after inactivity. Two-step verification (TOTP) is required for HQ and
for the roles each practice chooses. Every route states the roles it accepts; every practice query
filters by the caller's practice. Provider sessions are a separate token type valid for one request.

| Piece | How it works |
|---|---|
| Sign-in policy | `services.auth.sign_in_user` is the one place that decides, after a password or a Google identity, whether two-step is needed (`mfa_enabled`, HQ, or `practices.mfa_roles`) or a session starts. Each session start writes `signed in` to `access_log` (practice users) or `activity` (HQ), with the method |
| Practice open | `core.deps.ensure_practice_open` refuses a practice that is not `trial` or `active` (401) or whose `renews_on` is before today in the practice time zone (403 "This practice's plan ended on …"); login, the two-step step, refresh, Google and every authenticated request call it. HQ users are not affected |
| Forgot password | `POST /api/auth/forgot` counts the attempt, answers 204 at once, and only then (a background task with its own database session) looks the email up; an active or invited account gets a single-use `reset` token valid for one hour as `{APP_URL}/set-password#<token>`. Admins send the same email from Team. Setting the password ends every session |
| Google | server-side OpenID Connect with PKCE (`adapters/google_oidc.py`). `/api/auth/google/start` keeps state, nonce and the PKCE verifier in a signed ten-minute cookie (`bodha_google`, httpOnly, Secure, SameSite=Lax, path `/api/auth/google`); the callback checks the state, exchanges the code, verifies the ID token (RS256 against Google's keys, audience, issuer, expiry, nonce, verified email), finds the account by email, binds `users.google_sub` on first use and requires the same subject afterwards, then applies the sign-in policy and redirects to `/sign-in#signed_in`, `#mfa=<token>&setup=<0|1>` or `#error=<reason>` |
| Two-step secrets | stored as `v1:<Fernet token>` with `MFA_ENCRYPTION_KEY`; a secret without the prefix is a legacy plain value, accepted and re-saved encrypted after its first good code. `users.mfa_last_step` holds the last accepted 30-second step and a code is accepted only for a newer step |
| Recovery codes | ten single-use codes (`xxxx-xxxx-xxxx-xxxx`, about 79 bits each) made when two-step setup completes and returned once; stored as SHA-256 hashes in `recovery_codes`. `POST /api/auth/mfa/recover` uses one in place of the six digits; `POST /api/auth/recovery-codes` replaces them after a current six-digit code; an admin's two-step reset deletes them |
| Rate limits | `services.rate_limits.hit(db, rule, key)` stores one `rate_events` row per attempt (bucket, SHA-256 of the key, time) under a per-key advisory lock, so every API process shares the count; it deletes the key's expired rows and purges rows older than the longest window (`FOR UPDATE SKIP LOCKED`). Over the limit is a 429 "Too many attempts. Try again in N minutes." |
| Signed-in devices | `GET /api/auth/sessions` lists the caller's live refresh sessions (the refresh cookie marks the current one); signing one out, or every other one, revokes them and bumps the token version so their access tokens stop at once while this device refreshes silently |
