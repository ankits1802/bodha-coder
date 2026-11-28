# 0051 EHR connection: signed visit notes pulled over FHIR

Date: 2026-11-28

Context: practices bring visit notes in by upload, drop upload, a watched folder or email (0046). The
owner asked for notes to flow in from the practice's own EHR without anyone moving files: SMART on FHIR
Backend Services (OAuth 2.0 client credentials with a signed JWT client assertion), a key pair per
practice with the private half encrypted at rest and the public half at a per-practice JWKS URL, a test,
a resumable worker pull of finalized clinical notes, the same checks and batches as an upload, an
append-only record of every run and document, setup in Settings, and strict outbound safety.

## Choices

**Backend Services, nothing else.** Every vendor named (Epic, Oracle Health, athenahealth,
eClinicalWorks) registers a system client against a JWKS URL or a public key. Bodha posts
`grant_type=client_credentials`, the configured scopes, `client_assertion_type=urn:ietf:params:oauth:client-assertion-type:jwt-bearer`
and a JWT signed with the practice key: header `alg`, `kid`, `typ: JWT`; claims `iss` and `sub` the client
ID, `aud` the token endpoint, a random `jti`, `iat`, and `exp` 240 seconds later (SMART allows at most
five minutes). No `jku` is sent: a vendor that registered a static key would compare it with nothing it
holds. Tokens are kept in memory for one run, refreshed 30 seconds before they lapse and once on a 401.

**A key pair per practice, made by Bodha.** RS384 (RSA 3072) by default or ES384 (P-384), the two
algorithms SMART requires servers to accept. The `kid` is the RFC 7638 thumbprint of the public JWK.
The private key is PKCS#8 PEM sealed as `v1:<Fernet token>` under `EHR_KEY_ENCRYPTION_KEY`, a key of its
own in Secrets Manager rather than `MFA_ENCRYPTION_KEY`, so either can be rotated or lost without the
other. The Fernet code for two-step secrets moved into `core.sealed_text.TextSeal`, which both use. The
private key is never in an API answer, a log or the access log; only the API (to sign a test) and the
worker (to pull) open it. A new key retires the current one (`retired_at`, kept) and keeps the same
JWKS address; the JWKS lists only the current key, since Bodha signs only with it.

**The JWKS address carries a random key-set id, not the practice id.** `{APP_URL}/api/ehr/jwks/{32 hex}`
answers without sign-in. A purged practice's keys stop being published.

**The token endpoint is discovered and kept.** Saving reads `{base}/.well-known/smart-configuration`
through the same guarded client, refuses an EHR that lists auth methods without `private_key_jwt` or
grant types without `client_credentials`, and stores `token_endpoint` with the settings. It may be on
another host than the FHIR base (Oracle Health keeps it on its authorization host); it must be https on
a public address like every other request. The test reads the configuration again and fails if the
endpoint moved, so a vendor change is seen before a pull fails.

**Settings are revisions.** `ehr_connections` is append-only: every save, pause and resume adds a
revision (`change` `saved`, `paused`, `resumed`) with who made it; the current one is the highest
revision. Every change, the key and the test also go to the practice's access log ("connection saved for
the EHR", "connection key created for the EHR", "pulling from the EHR paused", "connection to the EHR
tested"), because the connection is what lets Bodha read PHI. Scopes must be `system/` scopes that let
Bodha read DocumentReference, Encounter and Practitioner; the default adds `system/Binary.read` and leaves
out `system/Patient.read`, because the note itself gives the analysis the patient details and the
minimum necessary is not to ask for more.

**What is pulled.** `DocumentReference?status=current&type=<LOINC codes>&date=ge<start>&_lastUpdated=ge<from>&_lastUpdated=lt<to>&_count=50`.
Note types are `progress` (11506-3), `consult` (11488-4), `history_physical` (34117-2) and
`nursing_facility` (34113-1, 34119-8, 34096-8, 67856-5, 34116-4, 68672-5, the nursing facility notes of
the HL7 LOINC document ontology value set; LOINC has no separate nursing facility progress note, so the
facility note stands for it). Servers ignore search parameters they do not support, so every filter is
checked again on what comes back: a document of another type or status, or written before the start
date, is counted as skipped on the run and gets no row. `docStatus` is not a search parameter in R4 and
must be `final`; a document without it is refused as `not_final` (fail closed), recorded per version so
the signed version is taken when it arrives.

**Where it goes.** The date of service is `Encounter.period.start` in the practice time zone, else
`DocumentReference.context.period.start`. The provider is the first referenced Practitioner (the note's
author, then the encounter's primary performer, attending, secondary performer, participant) whose
`http://hl7.org/fhir/sid/us-npi` identifier is a valid NPI of an active provider of the practice. The
place is a CMS place-of-service coding on the encounter, then the encounter class (EMER 23, IMP and
ACUTE 21, OBSENC 22, HH 12), then the provider's place, then 11 for an ambulatory encounter, then the
intake place of service, among the active places with a care setting. Location resources are not read
(no `Location.read` scope is asked for). The visit type is the intake visit type.

**Attachments.** PDF first, then HTML, then plain text; RTF and C-CDA XML are refused as
`unsupported_format` for now. Inline `data` is decoded; a URL is fetched with the attachment's type in
`Accept`, and a `Binary` answered as FHIR JSON is decoded. The declared `size` and `MAX_UPLOAD_MB` bound
it before and while downloading; a `hash` (SHA-1) that does not match refuses it. HTML is reduced to its
visible text with the standard library parser and, like plain text, set into a PDF with the existing
reportlab writer in reproducible mode, so the same note renders to the same bytes and checksum
duplicates still work.

**The same path as an upload.** The file gets the checksum name (`intake.arrival_name`), passes
`uploads.file_problem`, and a checksum already held makes the document a `duplicate` naming that note.
Otherwise `uploads.stage_intake_upload(..., source="fhir", opened=...)` stores it inside a savepoint:
one batch per provider, date of service and place for the whole run (later documents of the same plan
join the batch opened earlier in the run), `batches.source` `fhir`, the `uploaded notes` access entry by
"Bodha EHR connection", analysis queued. Upload history shows EHR as the uploader. The document row is
committed with the note, so a row never names a note that was rolled back.

**Resumable without mutable state.** A run is a row written once: inserted at the start with the cursor
it starts from, finished once with the outcome, reason, counts and the new cursor. The cursor is the end
of the last fully read `_lastUpdated` window: windows of at most seven days, ending two minutes before
now so late commits on the EHR are not missed, gapless because each window starts where the last ended.
A run stops early after 200 pages, 200 documents or ten minutes as `partial`; a failure leaves no
cursor, so the next run starts from the last good one. Documents already recorded (by id and version,
for the same base URL) are skipped without a request, so a repeated window costs only its search pages.
Changing the base URL, the note types or the start date starts from the start date again. The worker
looks every minute and pulls each practice at most every 15 minutes, under a per-practice advisory lock.

**Records.** `ehr_documents` holds FHIR resource ids (document, version, encounter, practitioner) and
the outcome, reason, note, checksum and size; `ehr_pull_runs` holds the window, outcome, reason and
counts. Never a patient reference, name or note text, and nothing of the EHR's error text: the token
step reports the HTTP status and the OAuth `error` code only. Reasons a document is refused:
`not_final`, `no_attachment`, `unsupported_format`, `too_large`, `attachment_unavailable`,
`attachment_mismatch`, `file_refused`, `no_service_date`, `future_service_date`, `no_provider`,
`no_place`, `foreign_reference`, `upload_refused`. Admins see every run and every document with its
reason in Settings, Setup, EHR connection.

**Outbound safety in one adapter.** `adapters.guarded_http` is the only way out: https only, no user
name in the URL, the host's addresses resolved and every one required to be a global unicast address
(private, loopback, link-local such as the instance and task metadata addresses, shared, reserved,
multicast and IPv4-mapped forms refused), TLS verification always on, no proxies from the environment,
connect 5 s and read 20 s timeouts, a size limit on every answer (declared or streamed), at most three
attempts with 1 and 2 second backoff on timeouts, connection errors, 429, 502, 503 and 504, `Retry-After`
in seconds or as a date obeyed up to 30 s (a longer pause ends the run as `rate_limited`), and requests
to one EHR spaced at least 0.2 s apart. Redirects are followed by hand only within the same origin.
`adapters.fhir_client` adds that every followed link (next pages, references, attachments) must stay
under the configured base URL, else `foreign_link` ends the run or `foreign_reference` refuses the
document. The test is limited to ten an hour per practice.

**No large FHIR library.** Only the fields read are validated (pydantic models with extra fields
ignored), which keeps the dependency list as it was: httpx, PyJWT, cryptography and reportlab are
already pinned.

## Legal

The EHR is the practice's own system and the practice registers Bodha's client and key with its vendor
and turns the connection on, so the EHR vendor is not a Bodha subcontractor and the subprocessors page
does not change. The BAA's permitted uses did not say that Bodha may retrieve PHI from the Covered
Entity's systems, only that it reviews notes, so it now says that Business Associate may retrieve
visit notes and the related encounter and practitioner details from an electronic health record system
Covered Entity connects, at Covered Entity's direction and with the access it grants (BAA 1.2). The
privacy policy's scope paragraph now covers notes retrieved from a customer's own EHR at its direction
(1.4), and the security page describes the connection's safeguards (1.3).

## Follows

- Not verified against a live EHR. Next: the Epic on FHIR sandbox (backend system app, JWKS URL), the
  Oracle Health (Cerner) code console sandbox (a different token host), athenahealth's Preview
  environment, and the SMART Backend Services reference server (`bulk-data.smarthealthit.org`) for the
  token exchange. Many vendors require `patient` or `encounter` on DocumentReference searches and offer
  population access only through Bulk Data `$export` on a Group with `_since`; a second strategy on the
  same records and cursor may be needed per vendor.
- Tasks run with public IPs that change with each task; an EHR that allow-lists source addresses needs a
  NAT gateway with an Elastic IP first.
- The address check and the connection use separate resolutions, so a name re-pointed between them
  could reach another address; TLS verification against the configured host name is what still stops it
  reaching an internal service, which would need a certificate for that name. Pinning the checked
  address in a custom httpcore network backend would close it.
- `EHR_KEY_ENCRYPTION_KEY` takes a comma-separated list for rotation like `MFA_ENCRYPTION_KEY`; losing
  it means every practice makes a new key and registers it with its vendor again.
- `bodha_purge_practice` removes a practice's documents, runs, revisions and keys before its notes.
- An amended note (`docStatus` `amended`) is refused as `not_final`, and a later final version whose
  attachment differs becomes a note of its own. Taking it as a replaced PDF of the earlier note, as a
  coder can, is the next step once a vendor's amendment behaviour has been seen.
