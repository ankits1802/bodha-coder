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
| `note_texts` | the note's text: a `document` revision for each PDF (extracted text, or empty for a scan until the model's text is stored as the next `document` revision), then one per signed addendum. A read uses the texts from the latest `document` revision onward | append-only |
| `analyses` | one row per model run or re-derivation: inputs (context), model, prompt version, tokens, validated report, raw response key | append-only; older runs become `superseded` |
| `suggestions` | each suggestion of an analysis: kind, codes before and after, action, reasoning, evidence quotes, severity, detail | belong to one analysis |
| `decisions` | each choice a person made on a suggestion | append-only; the latest per key applies |
| `code_sets` | billed and final code lists | append-only revisions per kind |
| `addendum_requests` | questions sent to a provider, the answers and the signed addendum | one per request |
| `access_log` | every PHI read, change and export (who, what, when, from where) | append-only; rows older than the practice's retention are purged |
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
| `practices/{practice}/notes/{note}/document-r{revision}.pdf` | an amended PDF that replaced it; `revision` is its `note_texts` revision. Earlier PDFs are kept |
| `practices/{practice}/notes/{note}/analyses/{revision}.json` | every raw model reply of that analysis |

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
   suggestion. Approval writes a final code set revision.
6. Asking the provider stores the questions and emails or texts a link whose token travels in the
   URL fragment. The provider confirms a one-time code sent to the contact on file, answers, and
   signs; the answers become a new note text revision and a new analysis is queued.

## Records: replaced PDFs, retention and practice deletion

| Piece | Flow |
|---|---|
| Replace a PDF | `POST /api/notes/{id}/document` (uploaders; `services.records.replace_document`). Refused for an exported note, a note being read, an open provider request, a file that is not a PDF or is too large, the same file, or a file another note already holds. The new PDF is stored under `document-r{n}.pdf` and becomes `notes.file_key`; the old object stays. A `document` text revision `n` holds the extracted text, or an empty string for a scan. Queued analyses of the note become `superseded`, a new one is queued with reason `document`, the note returns to `queued` (an approval is cleared) and the access log records `replaced PDF`. The note view shows the texts from the latest document onward |
| Access-log retention | `practices.access_log_years`, 6 (default) to 10, set by an admin on Security (`PUT /api/practice/security`). `services.records.purge_access_logs(db, now)` deletes each practice's rows created before the start of the practice-local day that many years before `now`, and returns the count; the worker calls it once a day |
| Delete a practice | HQ only, after the practice is `ended` or `blocked`: `DELETE /api/hq/practices/{id}` with `confirm_name` equal to the practice name. `services.records.delete_practice` deletes, in foreign-key order, decisions, suggestions and texts of its notes, its addendum requests, analyses and code sets, notes, batches, providers, MIPS list, access log and activity, its users' tokens, sessions and recovery codes, its users and the practice; then writes one `activity` row `practice deleted` (practice id, name) and removes every object under `practices/{id}/` (`ObjectStore.delete_prefix`: `list_objects_v2` pages, `delete_objects` in batches of 1000) |
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
| Risk adjustment | With the `hcc` check, the model lists suspected conditions only. `codes/hcc.py` loads the vendored CMS-HCC V28 files for the payment year (date of service year + 1), maps billed and documented ICD-10-CM codes to payment HCCs with the CMS age and sex edits and hierarchies, and scores both sets from the CMS relative factors. `services.risk_adjustment` stores the result as one `diagnosis` suggestion with key `hcc` (action `info`) and each new suspected condition as a `diagnosis` question (`hcc:<code>`, `ask`) |
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
[0012](decisions/0012-vertex-ai.md).

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
