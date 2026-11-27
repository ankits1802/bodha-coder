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
with a fresh link. Once a day it deletes stored files that no record holds (the orphan sweep, below).
Every 15 minutes it brings each live subscription's billed quantity in line with the practice's active
providers (Plans and billing, below).

## API types

Request bodies are pydantic models (`api/bodies.py`, `api/quality_bodies.py`). Services build each
response as a dictionary; the route declares its pydantic response model with `response_model=`,
from `api/responses/<area>.py`. The types flow one way:

| Step | Where | Rule |
|---|---|---|
| Route | `api/routes/<area>.py` | every JSON route names a response model. File downloads (claims CSV, defense packet PDF, addendum text) declare their media type with `responses.base.file_download`; the Google redirects declare `RedirectResponse`; 204 routes have no body |
| Validation | `responses.base.View` | `extra="forbid"`: a key the service builds but the model does not declare fails the request (500) and the test that reaches it, so the model and the service cannot drift silently |
| Errors | `responses.errors` | every non-2xx JSON body is `{"error", "message"}` (`ErrorResponse`, codes in `core.errors.ERROR_CODES`). Each operation documents `422` (takes input), `401` (needs a session), `403` (role guard) and `default`, read from its dependency tree; unknown routes, wrong methods and unhandled exceptions answer in the same shape, the last with a fixed message |
| Exact keys | `responses.base.ExactRoute` | every router uses it; it serialises with `exclude_unset`, so a response carries exactly the keys the service built. A key a service may leave out is declared `Omittable[...] = None` (optional in the schema, never `null`) |
| Document | `tools/export_openapi.py` | writes `frontend/openapi.json` (sorted keys, LF) from `app.main.app.openapi()` with placeholder settings, no database |
| Frontend | `npm run api:types` | `scripts/api-types.mjs` runs openapi-typescript on `openapi.json` and prints `src/lib/api/schema.ts` without comments |
| Screens | `src/lib/api/types.ts` | named aliases over `components["schemas"]` (`NoteDetail`, `QueueRow`, …) and the literal unions derived from them (`NoteStatus = NoteSummary["status"]`). Hand-written there: query and form types the client composes (`QueueQuery`, `UploadPlan`, `InviteBody`, …) and `MdmElements`, the reading of a finding's free-form `detail` |

CI regenerates both files (backend job: `openapi.json`; frontend job: `schema.ts`) and fails on any
difference. Decision: [0022](decisions/0022-typed-responses.md).

## Data model and revisions

Nothing a person or the model produced is overwritten.

| Table | Holds | Revisions |
|---|---|---|
| `notes` | one visit document: file, patient, date of service, provider, place, lane, headline | current state only; everything below is the history |
| `note_texts` | the note's text: a `document` revision for each PDF (extracted text, or empty for a scan until the model's text is stored as the next `document` revision), then one per signed addendum. A read uses the texts from the latest `document` revision onward | append-only |
| `analyses` | one row per model run or re-derivation: inputs (context), model, prompt version, tokens, validated report, raw response key | append-only; older runs become `superseded` |
| `suggestions` | each suggestion of an analysis: kind, codes before and after, action, reasoning, evidence quotes, severity, detail | belong to one analysis |
| `decisions` | each choice a person made on a suggestion, and each diagnosis-pointer choice for a claim line (`pointers:<code>:<diagnoses>`) | append-only; the latest per key applies |
| `code_sets` | billed and final code lists; a final procedure line carries its `pointers` when the coder linked them | append-only revisions per kind |
| `addendum_requests` | questions sent to a provider, the answers and the signed addendum | one per request |
| `access_log` | every PHI read, change and export (who, what, when, from where); `actor_kind` is `user`, `provider` or `system` (intake and auto-approval) | append-only; rows older than the practice's retention are purged |
| `activity` | administrative changes (setup, team, MIPS list, HQ) | append-only |
| `recovery_codes` | hashed single-use two-step recovery codes per user | replaced as a set |
| `user_identities` | the sign-in service subject bound to a user (`provider` `google`, `microsoft` or `yahoo`, `subject`); one per user and provider, one user per provider subject | added on first use, deleted with the user |
| `practices.signup` | how the practice began: `{"source": "hq"}`, or for self sign-up `source` `self`, `agreement_version`, `accepted_at`, `accepted_by` (user id), `method` (`email` or the provider) and `ip` | written once when the practice is created |
| `rate_events` | one row per counted attempt (bucket, hashed key, time) | deleted once outside the window |
| `subscriptions` | a practice's paid subscription (one per practice): `provider` (`stripe`, `paypal`), customer and subscription ids, `plan`, `interval` (`monthly`, `annual`), `status` (`pending`, `active`, `past_due`, `canceled`, `expired`), `current_period_end`, `cancel_at_period_end`, `quantity`, `past_due_since` | current state, written only from verified webhooks and the quantity sync; history in `activity` |
| `billing_events` | each processed Stripe or PayPal webhook (primary key provider and event id, kind, received) | written once; a repeat is ignored |
| `remittances` | one 835 payment (ST/SE transaction) of an uploaded file: payer, payment date, file key, the file's SHA-256 (`file_sha256`) | one per payment; a file with several payments shares its key |
| `remittance_lines` | each service line paid: claim reference, patient, date of service, billed and paid codes and amounts (cents), CAS adjustments, status, the plan type whose appeal window applies (`appeal_plan_type`, appealable lines only), matched note; `appeal_by` holds the date written by uploads before migration 0007 | written once at upload |
| `audit_runs` | one blind audit or training set: purpose, scope, provider or specialty, period, notes requested, who started it, status (`done` once every note is coded) | one per draw |
| `audit_samples` | each sampled note of a run (`run_id`): reviewer, position, the frozen Bodha and claim references, the answer and its agreement | coded once |

The models declare no ORM relationships, so a flush does not order inserts by foreign key and ids
are assigned at flush: flush a new row before adding rows that reference it.

The queued `analyses` row is the job. The worker records `attempts`, `error` and timing on it.

## Object storage (S3 or R2)

| Key | Content |
|---|---|
| `practices/{practice}/notes/{note}/document.pdf` | the uploaded PDF |
| `practices/{practice}/notes/{note}/document-r{revision}.pdf` | an amended PDF that replaced it; `revision` is its `note_texts` revision. Earlier PDFs are kept |
| `practices/{practice}/notes/{note}/analyses/{revision}.json` | every raw model reply of that analysis |
| `practices/{practice}/remittances/{remittance}.835` | an uploaded 835 file as received (the id of its first payment) |
| `practices/{practice}/inbox/{provider folder}/{YYYY-MM-DD}/{file}.pdf` | a PDF dropped for automatic intake, named by the practice until the first poll that sees it renames it to `{sha256}.pdf` (`{sha256} - {CPT}.pdf` when the name carried a CPT code) in the same folder; moved out once read |
| `practices/{practice}/evaluations/{run}/{case}-{attempt}.json` | the raw replies of each read of an evaluation case |
| `practices/{practice}/inbox/processed/{day}/{sha256}.pdf` | a dropped PDF that became a note (the note keeps its own copy) |
| `practices/{practice}/inbox/rejected/{day}/{sha256}{ext}` and `….reason.txt` | a dropped file that was refused, and the reason with its path after renaming |
| `ses-inbound/{recipient}/{message}` | a raw email stored by SES for email intake; deleted by the intake function once read ([infra/ses_intake](../infra/ses_intake/README.md)) |

Keys carry ids only, never names. PDFs are opened through signed links that expire after
`PDF_LINK_SECONDS`.

## How a note flows

1. `POST /api/uploads` validates every file first (PDF signature, size, billed codes), stores
   the PDFs, and creates a batch, notes, billed code set revision 1 and a queued analysis each.
2. The worker claims the analysis, takes the note texts from the latest `document` revision onward
   (or extracts the PDF text, or sends the PDF itself when it has no text layer), and calls `ai.review.review_note` with the
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
   suggestion, with the latest diagnosis pointers on each procedure line. Approval writes a final
   code set revision. Until export an approval can be undone (`POST /api/notes/{id}/reopen`, or
   `POST /api/notes/reopen` for several, all or none); the final code set stays as history and
   `reopened` is logged.
6. Asking the provider stores the questions and emails or texts a link whose token travels in the
   URL fragment. The provider confirms a one-time code sent to the contact on file, answers, and
   signs; the answers become a new note text revision and a new analysis is queued.

## Records: replaced PDFs, retention and practice deletion

| Piece | Flow |
|---|---|
| Replace a PDF | `POST /api/notes/{id}/document` (uploaders; `services.records.replace_document`). Refused for an exported note, a note being read, an open provider request, a file that is not a PDF or is too large, the same file, or a file another note already holds. The new PDF is stored under `document-r{n}.pdf` and becomes `notes.file_key`; the old object stays. A `document` text revision `n` holds the extracted text, or an empty string for a scan. Queued analyses of the note become `superseded`, a new one is queued with reason `document`, the note returns to `queued` (an approval is cleared) and the access log records `replaced PDF`. The note view shows the texts from the latest document onward |
| Access-log retention | `practices.access_log_years`, 6 (default) to 10, set by an admin on Security (`PUT /api/practice/security`). `services.records.purge_access_logs(db, now)` deletes each practice's rows created before the start of the practice-local day that many years before `now`, and returns the count; the worker calls it once a day |
| Delete a practice | HQ only, after the practice is `ended` or `blocked`: `DELETE /api/hq/practices/{id}` with `confirm_name` equal to the practice name. `services.records.delete_practice` deletes, in foreign-key order, decisions, suggestions and texts of its notes, its addendum requests, analyses and code sets, notes, batches, providers, MIPS list, access log and activity, its users' tokens, sessions and recovery codes, its users and the practice; then writes one `activity` row `practice deleted` (practice id, name) and removes every object under `practices/{id}/` (`ObjectStore.delete_prefix`: `list_objects_v2` pages, `delete_objects` in batches of 1000); objects a failed removal leaves are deleted by the orphan sweep |
| Orphan sweep | `services.file_sweep.sweep_orphan_files(db, store, now) -> int` (objects deleted), once a day from the worker under a Postgres advisory lock on its own connection, so one worker sweeps at a time. It lists the practice folders under `practices/` and each folder page by page (`ListingStore.list_folders`, `object_pages`). In a practice's folder an object older than 24 hours (S3 `LastModified`) is deleted when no row holds it: a note's `document.pdf`, its `file_key` and `document-r{n}.pdf` for each `document` text revision `n`; an `analyses.response_key`; a `remittances.file_key`; an evaluation reply of a case listed in its run's `results`. The intake folders (`inbox`, `inbox-…`) and keys of any other shape are left alone. A folder whose practice row is gone is emptied of objects older than 24 hours only when HQ activity holds `practice deleted` for it; otherwise it is left. One log line with counts only: `deleted`, `kept`, `recent`, `intake`, `unknown`, `unknown_folders` |
| HQ administration | `/api/hq/practices` rows carry the first admin (`admin_name`, `admin_email`, `admin_status`; a blocked admin only when no other). `POST /api/hq/practices/{id}/admin-link` resends an invited admin's invite or sends an active admin a password reset; `POST /api/hq/practices/{id}/renew` sets `renews_on` one year after the later of today and the current date. Both write `activity` |
| Paging | `/api/batches` (50), `/api/billing` (100, the export still takes up to 500), `/api/hq/activity` (100, filtered by `practice_id` and `action` on the server, with the list of actions) and `/api/access-log` (200) take `offset` and answer `items`, `total`, `offset`, `page_size` |

Decision: [0011](decisions/0011-practice-deletion-and-retention.md).

## Practice setup: credentialing and payers

| Piece | Flow |
|---|---|
| Credentialing | `providers.details` holds `taxonomy_code` (NUCC, 10 characters ending in X), `license_number` with `license_state` (US state or territory), `dea_number` (DEA check digit), `bills_under` (`individual` or `group`), `group_npi` (NPI check digit), `supervising_physician` and `signature_on_file`; `services.provider_details.validated_details` checks them for the provider dialog and for CSV import, where they are extra columns. Editing a provider without `details` keeps them |
| Payers | `practices.setup["payers"]["list"]`: `id`, `name` (unique, any case), `payer_id` (2 to 15 letters, digits or hyphens, stored in capitals), `plan_type` (`commercial`, `medicare`, `medicaid`, `other`) and `active`, changed through `POST`, `PUT` and `DELETE /api/practice/payers` (`services.payers`). The Insurance payers section is complete with its clearinghouse and EFT/ERA fields and at least one active payer; saving those fields keeps the list |

## Modifiers, add-on codes and risk adjustment

| Piece | Flow |
|---|---|
| Modifiers | The E/M answer names each modifier and its code. `services.code_additions` keeps those in `codes/modifiers.py` (visit or procedure set) for a code on the claim as a `modifier` suggestion (`add`, code before to code with modifier); a visit modifier follows the suggested level. Others become `review` suggestions. `routing.claim` appends accepted modifiers to the claim's E/M code or to the named code |
| Add-on codes | Each add-on the E/M answer names becomes a `code_review` suggestion (`add`, `addon:<code>`) when `is_known_cpt` accepts it, its units are 1 to 99 and it is not billed; otherwise `review`. Accepted ones are added to the claim once, with the units the answer gives (`detail.units`) |
| Units | `Code.units` (1 to 99) rides in the code set JSON (`"units"`, absent means 1). Code lists read `96127x2`, `96127 x 2` or `96127×2`; labels show `96127 ×2`; the CSV `cpt` column writes `96127x2`. `routing.claim` keeps units through replacements and modifiers |
| Risk adjustment | With the `hcc` check, the model lists suspected conditions only. `codes/hcc.py` loads the vendored CMS-HCC V28 files for the payment year (date of service year + 1), maps billed and documented ICD-10-CM codes to payment HCCs with the CMS age and sex edits and hierarchies, and scores both sets from the CMS relative factors. The age is the age on 1 February of the payment year (`payment_year_age`) when the model read a date of birth in the note (`patient.birth_date`, kept on `notes.patient_birth_date` when not after the date of service); otherwise the age in the note, and the summary carries `age_from` `note` ("Age from note"). Only the PY2027 initial mapping is published and vendored, so FY2027 codes map to no HCC. `services.risk_adjustment` stores the result as one `diagnosis` suggestion with key `hcc` (action `info`, with `age` and `age_from`) and each new suspected condition as a `diagnosis` question (`hcc:<code>`, `ask`) |
| MIPS status | Each eligible measure carries `met`, `missing` or `not_applicable`; the suggestion detail holds it |

Decision: [0010](decisions/0010-modifiers-add-ons-and-hcc.md), units in [0014](decisions/0014-units-and-medicare-national-estimates.md).

## Medicare national estimates

Every amount is an estimate of the Medicare national amount, never the practice's payment.

| Piece | Flow |
|---|---|
| Data | `codes/fees.py` loads `codes/data/pfs_rvu_2026.tsv.gz` (CMS CY 2026 PFS RVU26D, nonQPP PPRRVU, blank-modifier rows) after checking it against `pfs_rvu_2026.meta.json` (SHA-256, code counts, conversion factor 33.4009), once per process |
| Amount | per unit (work + practice expense + malpractice RVU) × conversion factor, rounded to the cent, times units; facility or non-facility practice expense from the place of service (`rate_setting_for`, Claims Processing Manual ch. 12 §20.4.2). Status other than A, R, T, zero RVUs, a payment-changing modifier, an unknown place or another calendar year give no amount |
| Note review | `services.estimates.note_estimate` prices the latest billed codes and the derived claim; the note detail carries `estimate` (release, setting, both sides with lines, unpriced codes, difference) |
| Billing | each row carries `estimate`, the priced total of its final codes |
| Insights | `estimates`: the claim minus billed difference across notes approved in the period, and per provider; `people`: per approver, approvals, median minutes from the current analysis finishing to approval, and claims changed in review (`claim_changes`) |

Decision: [0014](decisions/0014-units-and-medicare-national-estimates.md).

## Gemini endpoint

`GEMINI_BACKEND` chooses the Gemini Developer API (`developer`, API key, Files API for PDFs over
14 MiB) or Vertex AI (`vertex`, `GOOGLE_CLOUD_PROJECT` and `GOOGLE_CLOUD_LOCATION`, Application
Default Credentials, PDFs inline up to 50 MiB; a larger PDF fails for good with "PDF too large for
Vertex inline; split it"). PHI goes through Vertex under Google's BAA. Decision:
[0012](decisions/0012-vertex-ai.md). `demo` answers with canned reviews (`adapters/demo_model.py`)
and is refused at start-up when `APP_ENVIRONMENT` is `production` (the default):
[0023](decisions/0023-demo-model-backend.md).

## Web client data

| Piece | How it works |
|---|---|
| Cache | `hooks/remoteCache.ts` keeps loaded values in memory for a few seconds to minutes: lookups (places, payers, providers) for five minutes, the review order of a lane for two minutes, a prefetched note for one minute. It is emptied when the session ends, and nothing is written to browser storage |
| Prefetch | while a note is open, the next note of the lane is loaded; Today loads the first note waiting for a coder, and compliance the next case. A prefetch is an ordinary `GET /api/notes/{id}` and is written to the access log as `opened note` like any read |
| Decisions | a choice shows at once and is saved in order (`PUT /api/notes/{id}/decisions`); approval waits for the saves still running, and a failed save puts the last saved state back with the error |
| Remembered filters | the queue lane, assignee and provider filters and the compliance segment are kept per user in local storage (ids and lane names, never the search text) and restored when the screen opens without filters |
| Homes | billers start on Ready to bill and compliance on Compliance; other practice roles on Today |

## Calendar days

Each practice has a time zone (HQ sets it). Due dates (the end of the day of service plus the
turnaround), the addendum date, insights per day, recent batches and the access-log day are all
computed in that zone through `app/core/calendar.py`. Instants are stored and sent in UTC.

## Lanes

`notes.lane` is the worklist, `notes.lane_reason` says why in a fixed vocabulary (`flagged`,
`levels_too_high`, `audit_risk`, `waiting_on_provider`, `code_changes`, `questions`, `matches`), and
`notes.headline` is the sentence people read. Screens sort and filter on the reason, never the
headline.

## Assignment, daily summary and search

| Piece | Flow |
|---|---|
| Assignment | `notes.assigned_to` names the person working a note. `POST /api/notes/assign` (`services.assignment.assign_notes`): an admin assigns any active user of the practice with a note-reading role, or nobody; a coder or CDI specialist takes an unassigned note or releases their own. Only open notes (`queued`, `reading`, `ready`, `failed`) take a change; approving, exporting or deleting clears nothing. Each change writes `assigned` (detail `to <name>` or `to nobody`) to `access_log`. `GET /api/notes?assigned=me\|none\|<user id>` filters the queue; rows carry `assigned_to` and `assignee_name` |
| Daily summary | `services.digests.send_due_digests(db, messenger, now)` runs from the worker every five minutes. A practice that is open (trial or active, plan not ended) is due once its local time is 07:00 or later and no `activity` row `digest sent` holds its local date; a per-practice advisory lock keeps two workers from both sending. Each active note reader with `users.notify_digest` gets counts only (waiting by lane, due within 24 hours, assigned to them) and `{APP_URL}/today`, never a patient detail. People turn it off on Security (`GET`/`PUT /api/auth/preferences`) |
| Search | `GET /api/search?q=` (note readers, 2 to 100 characters) matches the practice's notes in every status by patient, file or provider name (`ILIKE`, wildcards escaped) or by a code on the latest billed or final code set (`code_forms` normalises `e119` to `E11.9`); 50 results, newest date of service first. The access log records `searched` with the count only |

## Provider requests

A provider token is bound to one request. After verifying, `GET /api/respond/others` lists the same
provider's other requests in the same practice that are `sent` and not expired (patient, date of
service, sent, question count), and writes `listed open requests` per note. `POST /api/respond/switch`
checks that the target belongs to the same provider and practice, is `sent` and not expired, writes
`switched request`, and returns a new provider token for it; anything else is 404. The provider page
offers the list and, after signing, the next request.

Decision: [0015](decisions/0015-assignment-digests-and-provider-switch.md).

## Security

Access tokens live in memory and carry a version; blocking, a role change, a password set or a
two-step reset bumps the version and revokes refresh sessions. Refresh tokens rotate on every use,
are stored hashed, and expire after inactivity. Two-step verification (TOTP) is required for HQ and
for the roles each practice chooses (admins by default). Every route states the roles it accepts; every practice query
filters by the caller's practice. Provider sessions are a separate token type valid for one request.

| Piece | How it works |
|---|---|
| Sign-in policy | `services.auth.sign_in_user` is the one place that decides, after a password or a Google identity, whether two-step is needed (`mfa_enabled`, HQ, or `practices.mfa_roles`) or a session starts. Each session start writes `signed in` to `access_log` (practice users) or `activity` (HQ), with the method |
| Practice open | `core.deps.ensure_practice_open` refuses a practice that is not `trial` or `active` (401) or whose `renews_on` is before today in the practice time zone (403 "This practice's plan ended on …"); login, the two-step step, refresh, the sign-in services and every authenticated request call it. HQ users are not affected |
| Forgot password | `POST /api/auth/forgot` counts the attempt, answers 204 at once, and only then (a background task with its own database session) looks the email up; an active or invited account gets a single-use `reset` token valid for one hour as `{APP_URL}/set-password#<token>`. Admins send the same email from Team. Setting the password ends every session |
| Sign-in services | server-side OpenID Connect with PKCE for Google, Microsoft and Yahoo: one client (`adapters/oidc.py`) driven by a registry (`adapters/oidc_providers.py`: discovery address, scopes `openid email profile`, settings, algorithms, issuer rule, email-trust rule). `/api/auth/{provider}/start` keeps state, nonce and the PKCE verifier in a signed ten-minute cookie (`bodha_oidc`, httpOnly, Secure, SameSite=Lax, path `/api/auth/{provider}`); the callback checks the state and the provider, exchanges the code, verifies the ID token (signature against the provider's published keys, audience, expiry, nonce, the provider's issuer rule and its verified-email rule; Microsoft's issuer must name the token's own tenant and its email counts only with `xms_edov` or a personal account), finds the account by email, binds the subject in `user_identities` on first use and requires the same subject afterwards, then applies the sign-in policy and redirects to `/sign-in#signed_in`, `#mfa=<token>&setup=<0\|1>` or `#error=<reason>&provider=<name>` (`no_account` only when self sign-up is off, `unverified_email`, `mismatch`, `blocked`, `plan_ended`, `rate_limited`, `failed`). With no account and self sign-up on it goes to sign-up instead (next row). A service is on only when its client id and secret are set; `GET /api/auth/providers` lists those and the sign-up options |
| Self sign-up | `services/signup.py` ([0026](decisions/0026-self-serve-sign-up.md)). Email: `POST /api/signup` counts the attempt (5 per address, 3 per email per hour), checks the agreement and the time zone, answers 204, then in a background task with its own session either sends an existing account a "sign in or reset your password" email or creates the practice and an `invited` admin and sends the set-password invite, so the answer never shows whether an email is registered. Provider: the callback sets `bodha_signup` (signed, 30 minutes, httpOnly, Secure, SameSite=Lax, path `/api/signup`, never in the URL) with provider, subject, email and name and redirects to `/sign-up/practice`; `GET /api/signup/identity` reads it (401 when missing or expired) and `POST /api/signup/identity` creates the practice and an `active` admin bound to the subject, clears the cookie and answers like sign-in (admins get the two-step setup challenge). Either way the practice is `trial` with `TRIAL_SEATS` seats until today plus `TRIAL_DAYS` in its time zone, `practices.signup` records the acceptance, and HQ activity gets `practice signed up`. With `SELF_SIGNUP_ENABLED=false` the routes answer 404; in production the API refuses to start with self sign-up on and no `BAA_URL` or `TERMS_URL` |
| Two-step secrets | stored as `v1:<Fernet token>` with `MFA_ENCRYPTION_KEY`; a secret without the prefix is a legacy plain value, accepted and re-saved encrypted after its first good code. `users.mfa_last_step` holds the last accepted 30-second step and a code is accepted only for a newer step |
| Recovery codes | ten single-use codes (`xxxx-xxxx-xxxx-xxxx`, about 79 bits each) made when two-step setup completes and returned once; stored as SHA-256 hashes in `recovery_codes`. `POST /api/auth/mfa/recover` uses one in place of the six digits; `POST /api/auth/recovery-codes` replaces them after a current six-digit code; an admin's two-step reset deletes them |
| Rate limits | `services.rate_limits.hit(db, rule, key)` stores one `rate_events` row per attempt (bucket, SHA-256 of the key, time) under a per-key advisory lock, so every API process shares the count; it deletes the key's expired rows and purges rows older than the longest window (`FOR UPDATE SKIP LOCKED`). Over the limit is a 429 "Too many attempts. Try again in N minutes." |
| Signed-in devices | `GET /api/auth/sessions` lists the caller's live refresh sessions (the refresh cookie marks the current one); signing one out, or every other one, revokes them and bumps the token version so their access tokens stop at once while this device refreshes silently |

## Plans and billing

Decision: [0028](decisions/0028-subscription-billing.md).

| Piece | How it works |
|---|---|
| Catalog | `services/plans.py`: `CATALOG` (trial, essentials, professional, enterprise; prices in cents per active provider, user and provider limits), `price_id(settings, provider, plan, interval)` from `STRIPE_PRICE_*` and `PAYPAL_PLAN_*`, `plan_for_price` (the reverse), `prices_complete`. `GET /api/plans` (public) lists the plans and the processors that are fully configured |
| Limits | `services/plan_limits.py`: users are capped by the plan, and also by `practices.seats` while no subscription is live; active providers by the plan. Invite, unblock, provider add or reactivation and CSV import answer 409 `the Trial plan allows up to 2 active providers` (or users), or `all seats are in use` |
| Plan screen | `GET /api/plan` (admins): plan, `standing` (`trial`, `active`, `past_due`, `canceling`, `canceled`, `managed`), `renews_on`, trial days left, users and active providers against their limits, and the subscription (`managed_by` `portal` for Stripe, `cancel` for PayPal) |
| Checkout | `POST /api/plan/checkout` `{plan, interval, provider}` (admins; essentials or professional; 409 while a subscription is live or when the practice has more active providers than the plan allows): Stripe Checkout in subscription mode (price for plan and interval, quantity `max(1, active providers)`, the admin's email or the known customer, `client_reference_id` and metadata `practice_id`, promotion codes) or a PayPal subscription (`plan_id`, quantity, `custom_id`), returning to `{APP_URL}/plan?checkout=done` or `=cancelled`. Answers `{url}`; writes `checkout started` |
| Manage | `POST /api/plan/portal` (Stripe Billing Portal session, or PayPal's automatic payments page) and `POST /api/plan/cancel` (Stripe `cancel_at_period_end`, PayPal cancel); neither changes stored state |
| Webhooks | `POST /api/billing-webhooks/{stripe,paypal}` (no session): verify the signature (400 otherwise), record the event in `billing_events` (a repeat answers 204 and does nothing), fetch the subscription from the processor and apply it (`services/subscription_events.py`): live states make the practice `active` on the subscription's plan with `renews_on` = the period end (or the grace end while past due); a canceled or expired subscription that was live keeps access to its period end; webhooks never lift a block. Writes `subscription changed` |
| Quantity | `services/quantity_sync.py`: after provider changes (a background task) and every 15 minutes (worker), each live subscription whose quantity differs from `max(1, active providers)` is updated (Stripe item quantity with prorations, PayPal revise); a failure waits for the next sweep. Writes `subscription quantity changed` |
| HQ | practices rows carry `billing_provider`, `billing_status`, `billing_interval`; while a subscription is live HQ cannot change plan or renewal (409), and the practice cannot be deleted |
| Web | `/plan` (Plan and billing, admins), the trial and past-due banner at the top of every admin screen (hidden for the day when dismissed, a local-storage date), and the public `/pricing` page |

## Defensibility

Three read-only checks back the claim a practice bills. None of them writes a review record; each
read is written to `access_log`.

| Piece | How it works |
|---|---|
| Audit defense packet | `GET /api/notes/{id}/defense-packet` (note readers, practice scope through `note_for`). `services.defense_packet` gathers the note, provider, place, billed and final code sets (the derived claim while not approved), the Medicare national estimate, the E/M finding (MDM elements and justification, or documented time), every change-kind suggestion whose latest choice is accept, keep or add with its reasoning and verbatim evidence, the code-set checks (ICD-10-CM release for the date of service, CMS fee schedule code list, CMS-HCC V28 when the risk summary exists), every provider request with its answers and the signed addendum labelled as an amendment with its signing time, the decision history (decisions, code-set revisions and the note's decision actions in `access_log`) and every analysis run with model and prompt version. `services.defense_layout` turns that into blocks and `adapters/pdf_writer.py` renders them with reportlab (Helvetica). The cover shows the patient's initials only; the file name is `bodha-defense-packet-<date of service>-<note id prefix>.pdf`. Writes `downloaded defense packet` |
| Same-provider day | `GET /api/notes/{id}/day` (note readers) and `GET /api/compliance/days?from=&to=` (compliance; default the last 30 days, at most 92). `services.day_checks` loads the provider's notes for the date of service, the documented minutes from the current analysis (`report.em.time_minutes`), the visit code (`services.visit_levels`: the final code set once approved, otherwise the latest billed set) and the latest `document` text. Flags: total time over 16 hours, a pair of notes whose text without its first and last three non-blank lines has character 5-gram Jaccard similarity of 0.85 or more, and a share of the two highest levels over 60% across five or more leveled visits. Writes `opened provider day` or `listed provider days` |
| E/M level mix | `GET /api/insights/em-mix?days=` (insight readers; 7, 14, 30 or 90 days of dates of service). `services.em_mix` counts each provider's visit codes per benchmarked family and compares the shares with the CMS CY 2025 *E/M Codes by Specialty* file (`codes/em_benchmarks.py`, checksummed manifest) for the provider's specialty. A level is an outlier when its share differs by more than 15 points with at least 10 visits in the family; a family is also an outlier when a chi-square goodness-of-fit test (`core/chi_square.py`, levels pooled until each expected count is at least 5) gives p < 0.01 with at least 30 visits. The lean is higher or lower by the mean level. A specialty that does not map to the CMS list has no benchmark |

Decision: [0018](decisions/0018-defensibility-features.md).

## Claim edits

Advisory checks on the claim a note bills. They change no suggestion and no lane; each read is
written to `access_log`.

| Piece | How it works |
|---|---|
| NCCI edits | `codes/ncci.py` loads the vendored CMS Medicare NCCI practitioner tables (`ncci_practitioner.meta.json`, checksummed): PTP edits (column 1, column 2, effective and deletion dates, modifier indicator), add-on code edits, and one MUE table per quarter, serving dates of service 2025-10-01 to 2026-12-31. An edit applies from its effective date through its deletion date (the CMS deletion date is the last day in effect); indicator 9 rows never applied and are not kept. `claim_edits(codes, service_date)` returns each PTP pair billed together with whether a modifier may bypass it and which one does (59, XE, XP, XS, XU, 27, 58, 78, 79, 91 on either line; 24, 25, 57 on the E/M line; an anatomic modifier the other line does not carry), each type 1 add-on billed without any of its primaries, and each code whose units exceed the MUE of the quarter of the date of service (MAI 1 per line, MAI 2 and 3 summed over the lines). Dates outside the loaded quarters raise `NcciUnavailable`. The PTP table stays one sorted text block searched by bisection (about 42 MB, loaded on first use) |
| Payer rules | `codes/payer_rules.py`: `payer_flags(claim, payer_type, place_code, service_date)` applies the rules of the payer's plan type (`medicare`, `medicare_advantage`, `medicaid`, `commercial`) and family (`cigna`, read from the payer name) and returns advisory flags with a severity (`denial`, `risk`, `reminder`). `repeated_initial_visit(codes, place_code, service_date, history, specialty=)` flags an initial nursing-facility visit (99304-99306 at POS 31 or 32) when the history holds an earlier one at POS 31 or 32 by the same specialty with no discharge (99315, 99316) from that day to this one: `initial_visit_repeated`, `denial`, with `earlier` |
| Claim checks | `GET /api/notes/{id}/claim-checks` (note readers): the current claim (`review_actions.current_claim`), its NCCI edits (empty, with `ncci.covers` false, outside the loaded quarters) and the payer flags for `notes.payer` (an id from the practice payer list); without a payer there are no plan flags. `initial_visit_repeated` is added with or without a payer: `claim_checks.stay_history` reads the practice's other notes up to the date of service for the same patient (`remittance_matching.same_person` on the names, and the same date of birth when both notes have one) with each note's visit code (`visit_levels.visit_codes`) and its provider's specialty. Writes `checked claim edits` |
| Claim lines | `POST /api/billing/claim-lines` `{note_ids?, format: json or csv}` (billers): 837P-ready lines for approved notes not yet exported, from the final code set: date and place of service, rendering NPI and taxonomy, billing NPI (the provider's own NPI when billing as an individual, otherwise the group NPI from provider details), diagnoses A to L without the period (more than 12 is refused), and per procedure line the code, up to four modifiers, units and its diagnosis pointers as letters (below). CSV cells go through `billing.safe_cell`. Notes are not marked exported. Writes `built claim lines` |
| Diagnosis pointers | `GET /api/notes/{id}/pointers` (note readers; writes `opened diagnosis pointers`) lists the claim's diagnoses with their letters A to L and each procedure line with its pointers and whether the coder chose them (`stored`): the current claim, or the final code set once approved. `PUT /api/notes/{id}/pointers` `{lines: [{code, pointers}]}` (deciders, ready notes; writes `linked diagnoses`) takes up to four distinct ICD-10-CM codes on the claim per procedure code on the claim, in order; an empty list returns the line to the default. Each line becomes a `decisions` row (`pointers:<code>:<diagnoses>`, choice `accept`); `review_actions.current_claim` puts the latest on its line and drops a diagnosis that has left the claim, and approval writes them into the final code set. Default for a line without one: an add-on (NCCI add-on table for the date of service, `claim_lines.add_on_primaries`) carries its primary's pointers, every other line points to the first four diagnoses (`claim_lines.line_pointers`). In note review each procedure chip in the claim bar shows its letters and opens the pointer editor |
| Refresh | `python tools/fetch_ncci.py --quarter <YYYYQn> --ptp-version <vNNNr0> --serves-from <date>` downloads the CMS zips (or reads them from `--sources`), checks every row, and writes the artefacts and the manifest with the SHA-256 of each zip, source file and artefact |

Decision: [0019](decisions/0019-ncci-edits-and-payer-rules.md).

## Remittance

Billers upload the payer's 835 (electronic remittance advice) and Bodha ties each paid line back to
the note it billed.

| Piece | How it works |
|---|---|
| Upload | `POST /api/remittances` (billers, multipart `file`). The raw file is stored at `practices/{practice}/remittances/{id}.835` and its SHA-256 on every payment row; a file whose checksum matches an earlier upload of the practice is refused whatever its name (409 `this file was already uploaded on {day} as {name}`, the practice-local day of the first upload). The check runs under a per-practice advisory lock, after payments stored without a checksum are given theirs from their stored file. Writes `uploaded remittance` |
| Parser | `services/x12.py` reads the envelope strictly: the separators from the fixed-width ISA, ISA/IEA, GS/GE and ST/SE nesting, control numbers and counts. `services/remittance_835.py` reads BPR, TRN, DTM*405, N1*PR (and REF*2U), CLP, NM1*QC, DTM*232/472, SVC and CAS, and refuses a service line that does not balance (SVC02 − CAS = SVC03) or a payment that does not (Σ CLP04 − Σ PLB = BPR02). Errors are 422 with the segment named |
| Codes | per X12, SVC01 is the code the payer adjudicated and SVC06 the code submitted when it differs: billed = SVC06 or SVC01, paid = SVC01 |
| Matching | CLP01 is matched to a note id (the export carries it; a prefix of at least 8 characters, as payers may truncate to 20, when unique) and must agree with the date of service; otherwise patient name tokens (order and initials ignored) + date of service + billed CPT in the latest final (else billed) code set, when exactly one note fits |
| Status | `remittance_outcomes.line_outcome`: `denied` (CLP02 = 4, or nothing paid and nothing left to the patient), `downcoded` (paid a lower level of the same E/M family, or CO-150 / CO-152), `paid_as_billed`, `matched` (shown as Other: a different code, a reversal); a line with no note is `unmatched` |
| Appeal by | for denied and downcoded lines: payment date (BPR16, else DTM*405) + the window for the plan type. The plan type is Medicare for CLP06 MA/MB, Medicaid for MC, otherwise the practice payer list's type for the payer id or name, otherwise commercial. Windows default to Medicare 120 days (redetermination), Medicare Advantage 60 and 180 for the rest; admins change them with `PUT /api/remittances/appeal-days`. A line stores its plan type and the date is computed whenever lines are read (`remittance_outcomes.line_appeal_by`: list, detail and letter), so a change of window moves every date at once; a line stored before plan types keeps its stored `appeal_by` |
| Appeal letter | `GET /api/remittances/lines/{id}/appeal` re-reads the stored file for the member id and payer claim number and returns plain text (`services/appeal_letters.py`: redetermination for Medicare, reconsideration otherwise) with `defense_packet` = `/api/notes/{note}/defense-packet`. Writes `drafted appeal` |
| Screen | `/remittances` (billers): files with status counts and the first appeal-by date, the selected file's lines with filters (downcoded, denied, unmatched), and the letter with copy, download and the defense packet. Viewing lines writes `viewed remittance` |

## Intake

A practice can drop PDFs into its own prefix instead of uploading them.

| Piece | How it works |
|---|---|
| Settings | `practices.intake`: `enabled`, `prefix` (`inbox` or `inbox-…`, always under `practices/{practice}/`), `provider_by_folder` (folder → active provider), `place_code`, `visit_type`. `GET` and `PUT /api/practice/intake` (admins); the admin section is `components/shared/intake/IntakeSettings.tsx`. Writes `intake saved` |
| Layout | `practices/{practice}/inbox/{provider folder}/{YYYY-MM-DD}/{file}.pdf`; the day folder is the date of service. `processed` and `rejected` are reserved folder names |
| Poll | `services.intake.poll_intake(db, store, now) -> int` (notes created), with a `ListingStore` (`adapters/object_listing.S3ListingStore`). Each enabled, open practice is polled under a Postgres advisory lock held on its own connection (`pg_try_advisory_xact_lock`), so two workers never ingest the same practice at once. Files are grouped by folder and day; every file is first renamed in its folder to `intake.arrival_name`: the SHA-256 of its content, ` - {CPT}` when the name carried a CPT code, and its suffix, so a patient name in a file name lives at most one poll; a name already of that shape is kept. Then each is checked with the upload checks (`uploads.check_pdf`, `uploads.billed_codes_for`, codes from the renamed file name) and each group goes through `uploads.create_intake_upload` as one batch: `batches.source` `intake` with no `created_by`, billed code sets with no actor, and the `uploaded notes` access entry by `Bodha intake` (`audit_log.record_system_access`, actor id `bodha-intake`, kind `user` because the access log allows only user and provider). Upload history shows Intake as the uploader |
| Results | accepted files move to `inbox/processed/{day}/{sha256}.pdf`; files in the wrong place, of the wrong type, for an unmapped folder, a future date, a failed check or a duplicate move to `inbox/rejected/{day}/` with a `.reason.txt`. Writes the `uploaded notes` access entry and an `intake processed` activity with counts |

How a practice drops files: [DEPLOY-INTAKE.md](DEPLOY-INTAKE.md); the email intake function: [infra/ses_intake](../infra/ses_intake/README.md).

## Query governance

Provider queries follow the AHIMA/ACDIS compliant query practice (2026 draft, Section XI).

| Piece | How it works |
|---|---|
| Repeat queries | `query_governance.repeat_query_blocked(db, note, keys)` returns the keys already asked on the note (requests sent, answered or expired) with no note text revision since, other than the addendum that request produced; `refuse_repeat_queries` raises 409 for them |
| Metrics | `GET /api/insights/queries?days=` (insight readers; 7, 14, 30 or 90). Per provider and in total: queries (questions in requests that were not cancelled), queries per 100 notes uploaded in the period, answered share, median hours from sending to signing, agreed share (an answer other than No, Clinically undetermined or Other) and repeated share (a key already asked on the same note) |
| Escalation | `query_governance.escalate_unanswered(db, messenger, now) -> int`, hourly: requests still `sent` 48 hours after sending, not yet escalated and with a live link, are locked (`FOR UPDATE SKIP LOCKED`), and each practice's active admins get one email with the count and a link to the provider lane, no patient details. `escalated_at` is set and `provider requests escalated` is recorded; if no email could be sent the requests wait for the next hour |
| Addendum export | `GET /api/notes/{id}/addendum.txt?request_id=` (note readers): the signed addendum (the latest, or the request named) headed `ADDENDUM — dated {signed} — signed by {provider, credential} — refers to the visit of {DOS}`, dates in the practice time zone, for pasting into the EHR. Writes `exported addendum` |

Decision: [0017](decisions/0017-remittance-intake-query-governance.md).

## Quality programme

Bodha's accuracy is measured by people who cannot see what Bodha suggested, and autonomy is earned from
those measurements.

| Piece | How it works |
|---|---|
| Blind audit | `POST /api/quality/samples` (admin, compliance): `services.audit_samples.draw_sample` draws N approved or exported notes for the practice, a provider or a specialty with a date of service in the period (default 40, 150 for a specialty), shuffled with a seed recorded in the activity entry, and assigns them round-robin to the chosen reviewers, never to the person who approved the note. The draw is one `audit_runs` row (purpose, scope, provider, specialty, period, requested, `created_by`, status) and each note one `audit_samples` row with its `run_id` (`purpose` `audit`) and `result.position`. At drawing time `result.reference` freezes Bodha's suggested claim (billed codes with every suggestion at its default choice, from the current analysis, whose id is `analysis_id`) and the final claim. The run id is the sample id of every route. Writes `started blind audit` with the note count and seed |
| Blind form | `/quality/review/{sample}` and `/training/{sample}` (note readers). `GET /api/blind-review/{sample}/next` returns only the next open item of the caller: its id, position and the current note texts; `GET /api/blind-review/items/{item}/document` signs the PDF link. Nothing else about the note leaves the server. `POST /api/blind-review/items/{item}/answer` checks the E/M code, every ICD-10-CM code (billable in the release for the date of service) and the modifiers, stores the answer, compares it with both frozen references (`services.agreement.compare_elements`) and marks the run `done` when no item is left open (under a row lock on the run). While the caller has an open item for a note, `api/blinding.SightedReader` and `SightedDecider` (`blind_review.refuse_blind_note`) answer 403 "This note is in your blind audit" on `GET /api/notes/{id}`, its `/document`, `/defense-packet`, `/claim-checks`, `/day` and `/addendum.txt`, and on `PUT /api/notes/{id}/decisions` and `/billed-codes`; other users are unaffected. Writes `opened note for blind review` and `coded note blind` |
| Agreement | `services.agreement`: per note, E/M exact match and its direction (`higher`, `lower`, `family`, `absent`), ICD-10 matched, compared and reference counts with missing and extra codes, exact modifier set match. `summarize` gives Wilson 95% rates (`core.statistics.wilson`) for the per-note measures (E/M exact, Bodha higher, Bodha lower, ICD-10 exact set, modifiers) and per-note bootstrap 95% intervals (`core.statistics.bootstrap_ratio`: 2,000 resamples of the notes, fixed seed, 2.5th and 97.5th percentiles) for ICD-10 precision and recall, with their F1. `visit_agreement` is the E/M exact rate alone |
| Results | `GET /api/quality/samples` lists the runs of the practice with progress, status, reviewers, `started_by` and the E/M exact rates; `GET /api/quality/samples/{sample}` (admin, compliance): the summary against Bodha and against the final claim, the same per provider, and one row per note; the references of a note stay hidden until it is coded. Writes `opened audit results`. Screen: `/quality` (Blind audits), chart and table views |
| Evaluation set | `POST /api/quality/eval-cases` (admins) marks an approved note: `eval_cases.expected` holds the final claim, its E/M code, MDM level, ICD-10 codes and modifiers, and the analysis it came from |
| Evaluation run | `POST /api/quality/evaluations` (admins) queues an `eval_runs` row with `GEMINI_MODEL` and `PROMPT_VERSION`. The worker calls `services.evaluation_runs.run_next_evaluation` (or `run_evaluation(db, run_id, deps)`), which claims the row `queued` → `running` with `FOR UPDATE SKIP LOCKED`, rebuilds each case's review inputs from its analysis context and current note texts without writing to the note, runs `deps.review` twice, derives Bodha's claim from each report with `build_findings` and `claim`, stores the raw replies under `practices/{practice}/evaluations/{run}/{case}-{attempt}.json`, and records per case the agreement of the first read with the expected claim and of the two reads with each other. A case the model cannot read keeps its error; a run with no scored case is `failed` |
| Drift | `GET /api/quality/evaluations` lists runs with the model and prompt version and compares each finished run with the previous one: E/M exact, ICD-10 F1 or modifier agreement more than five points lower is `dropped`. `GET /api/quality/level-mix` compares the MDM level of Bodha's suggested E/M code on notes seen in the last 30 days with the 90 days before (chi-square test of homogeneity, sparse levels pooled, `shifted` below p 0.05, `not_enough` under 30 notes a window) |
| Earned autonomy | `services.autonomy.provider_eligibility`: the provider's notes in the latest `done` audit run that contains them (by its last coding time) must number at least 30, with the Wilson 95% lower bound of E/M exact agreement at least 90% and Bodha higher on at most 5%. `PUT /api/quality/providers/{id}/auto-approve` (admins) turns `providers.auto_approve` on only then. `services.auto_approval.auto_approve_eligible(db, note)` also needs the note ready in the approve lane with reason `matches`, never flagged or through compliance, no review items or critical audit risks, no open questions or sent request, the provider still eligible, and the note not one of the one in ten held for a person (`held_for_quality_check`: first eight hex digits of SHA-256 of the note id, modulo 10). `auto_approve(db, note)` writes the final code set with reason `auto` and no actor, and an `approved` access entry by `Bodha (auto)`; the caller commits |
| Training | `POST /api/training/sets` (admins) draws a set with `purpose` `training` for one trainee (an `audit_runs` row like an audit). `GET /api/training` lists every run with items assigned to the caller with running scores against the final claim; after each answer `GET /api/blind-review/items/{item}/feedback` shows the trainee's codes, the final claim, Bodha's suggestion and the suggestions with their evidence. Writes `opened training feedback` |

Decision: [0020](decisions/0020-measured-accuracy-and-earned-autonomy.md).
