# Shared components

Check here before writing a helper.

## backend/app/core

| Module | Provides |
|---|---|
| `config.py` | `Settings` (billing settings in `BILLING_SETTINGS` read blank as unset; refuses `GEMINI_BACKEND=demo` when `APP_ENVIRONMENT` is `production`, the default; `refuse_unready_signup()` raises `SignupNotReady` when production has self sign-up on without `BAA_URL` and `TERMS_URL`, called first in the API lifespan; blank `TERMS_URL`, `BAA_URL`, `PRIVACY_URL` read as unset; `ADMIN_URL` is empty or a bare web address on another host than `APP_URL` (trailing slash dropped), `FORWARDED_ALLOW_IPS` as uvicorn reads it; `can_send_texts` is true in development and otherwise only when `SMS_TRANSPORT` is `twilio` or `sns` with every setting `TEXT_SETTINGS` names for it), `site_host(address)`, `get_settings()` |
| `db.py` | `engine`, `SessionFactory`, `get_session` |
| `security.py` | `hash_password`, `verify_password`, `issue_token`, `read_token`, `digest`, `same_digest`, `random_token`, `random_code`, TOTP helpers (`mfa_step_for`, `mfa_uri`, `new_mfa_secret`), `seal_mfa_secret` / `open_mfa_secret` / `is_sealed_mfa_secret` (Fernet, `MFA_ENCRYPTION_KEY`), `MfaKeyUnavailable` |
| `errors.py` | `AppError` (400) and `Unauthorized`, `Forbidden`, `NotFound`, `Conflict`, `Invalid`, `Unavailable`, `RateLimited` (429) |
| `roles.py` | role groups used by every route guard, `HQ_ROLE` |
| `realms.py` | `Site` (`url`, `realms`, `takes_signups`), `request_site(request)` and `CurrentSite` (the site of the request's host: `ADMIN_URL` serves `hq`, any other host `practice`, one site for both when `ADMIN_URL` is empty), `site_for(host, settings)`, `public_host(request, settings)` (`Host`, or a trusted proxy's `X-Forwarded-Host`), `from_trusted_proxy(request, allowed)`, `realm_url(realm)` (where an account's emailed links point), `account_space(realm)` (the realms an email must be free in) |
| `calendar.py` | `zone_named`, `day_bounds`, `today_in` (practice calendar days), `shift_years(day, years)` (29 February becomes the 28th in a common year) |
| `deps.py` | `Db`, `Actor` (`billing_only_since`: the day the plan ended, for a billing-only session), `session_actor` (any signed-in session, billing-only included), `current_actor` (refuses a billing-only session with `PlanEnded`), `require(*roles)` (over `current_actor`), `require_for_billing(*roles)` (over `session_actor`, for the plan routes only), `ProviderActor`, `current_provider`, `ensure_session_allowed(user, practice)`, `plan_ended_on(practice)`, `billing_only_since(user, practice)`, `PlanEnded(ended_on)` |
| `chi_square.py` | `chi_square_sf(statistic, degrees_of_freedom)` (closed forms for whole degrees of freedom), `pooled_cells(observed, expected, minimum=5)`, `goodness_of_fit(observed, expected) -> GoodnessOfFit \| None` (None when fewer than two pooled cells) |
| `statistics.py` | `wilson(successes, trials) -> Rate` (Wilson score 95% interval; `Rate.value/low/high` are None with no trials), `bootstrap_ratio(units, *, resamples=2000, seed=BOOTSTRAP_SEED) -> Rate` (ratio of summed parts to summed wholes with a percentile 95% interval from resampling the units, the unit of independence, with replacement; nearest rank, resamples with an empty denominator left out), `f1_score(precision, recall)`, `chi_square_homogeneity(first, second) -> ChiSquare \| None` (two periods over ordered levels, sparse levels pooled through `chi_square.pooled_cells`), `Z_95` |
| `logging.py` | `configure_logging()` (JSON lines on stdout for every process, uvicorn's access log off), `JsonFormatter` (adds the request id; exceptions as type, frames and cause types, never their message), `RequestLog` (ASGI middleware: one `bodha.access` line per request with method, route template, status, duration and request id; `X-Request-ID` in and out), `log_queue_metrics(logger, *, queued, running, at)` (CloudWatch Embedded Metric Format line, namespace `BodhaCoder`) |

## backend/app/codes

| Module | Provides |
|---|---|
| `icd.py` | `load_catalog()`, `IcdCatalog.for_service_date`, `IcdCatalog.describe(code, service_date)`, `IcdRelease.get / more_specific / is_unspecified`, `format_icd`, `fiscal_year_for` |
| `em.py` | `EM_FAMILIES` (each `EmFamily` with its levels and add-ons, such as 99292), `compare_em`, `describe_em`, `is_em_code`, `em_ladder(code)` (each level of the code's family as code and MDM level) |
| `modifiers.py` | `VISIT_MODIFIERS`, `PROCEDURE_MODIFIERS`, `allowed_modifiers(code)`, `modifier_meaning(code, modifier)` |
| `hcc.py` | `load_hcc_model(payment_year)`, `hcc_model_for(payment_year)` (None when not vendored), `HccModel.hccs_for / payment_hccs / score / label / factor / is_trumped`, `HccPatient`, `payment_year_for(service_date)`, `payment_year_age(birth_date, payment_year)` (age on 1 February of the payment year; None for a birth after that day), `segment_for(age)`, `sex_code`, `HccDataCorrupt` (CMS-HCC V28, checksummed manifest) |
| `billing_codes.py` | `Code` (`units`, `pointers` (up to `MAX_POINTERS` distinct ICD-10-CM codes, procedure lines only; JSON `pointers`, absent when none), `label()` `96127 ×2`, `as_text()` `96127x2`, `as_json` / `from_json`), `InvalidUnits`, `InvalidPointers`, `with_pointers(codes, pointers)` (stored choices onto their lines, diagnoses no longer on the claim dropped), `parse_code_list` (reads units), `claim_changes(final, billed)`, `parse_note_filename`, `is_known_cpt` |
| `fees.py` | `fee_schedule_for(service_date)` (None for a year not vendored), `load_fee_schedule(year)`, `FeeSchedule.unit_amount / line / estimate`, `ClaimEstimate` (`total`, `unpriced`), `rate_setting_for(place_code)`, `FeeDataCorrupt` (CMS CY 2026 PFS RVU26D, checksummed manifest) |
| `em_benchmarks.py` | `default_em_benchmarks()`, `load_em_benchmarks(year)`, `EmBenchmarks.shares(specialty, family) / specialty_for(text) / specialties()`, `BENCHMARK_FAMILIES`, `benchmark_family`, `cms_specialty_for`, `EmBenchmarkCorrupt` (CMS CY 2025 E/M Codes by Specialty, checksummed manifest; rebuilt by `tools/vendor_em_specialty.py`) |
| `ncci.py` | `claim_edits(codes, service_date)` (PTP pairs with `modifier_allowed` and `bypassed_by`, add-ons without a listed primary, units over the MUE), `ncci_tables()` (cached), `load_ncci(data_dir=)`, `NcciTables.covers / ptp_edit / add_on_primaries / mue_limit / claim_edits`, `PairEdit`, `UnitsEdit`, `AddOnEdit`, `NcciUnavailable` (date of service outside the loaded quarters), `NcciDataCorrupt` (CMS Medicare NCCI practitioner PTP, add-on and MUE tables, checksummed manifest; rebuilt by `tools/fetch_ncci.py`) |
| `payer_rules.py` | `payer_flags(claim, payer_type, place_code, service_date)` (advisory `PayerFlag`s: rule, severity `denial` / `risk` / `reminder`, codes), `repeated_initial_visit(codes, place_code, service_date, history, *, specialty=)` (`PayerFlag` `initial_visit_repeated` with `earlier` when an `EarlierVisit` opened the same nursing-facility stay), `initial_nursing_visits(codes, place_code)`, `payer_for(plan_type, name)` (`Payer` plan and family), `PayerClaim`, `PLAN_TYPES` |
| `adjustment_reasons.py` | `ADJUSTMENT_GROUPS` (CAS group codes), `DOWNCODE_REASONS` (CARC 150, 152), `CONTRACTUAL`, `PATIENT_RESPONSIBILITY`, `describe_adjustment(group, reason)` |
| `places.py` | `setting_for(place_code)` |
| `npi.py` | `is_valid_npi` |
| `credentials.py` | `is_taxonomy_code` (NUCC: 10 characters ending in X), `is_valid_dea` (DEA shape and check digit), `LICENSE_STATES` (50 states, DC and five territories) |
| `mips_catalog.py`, `cms_mips_2026.py`, `mips_reporting_codes.py` | CMS MIPS 2026 catalog, standard measures, reporting codes (vendored from ChartMate) |
| `mips_scope.py` | `MipsScope`, `validate_measure_ids`, `practice_scope` |

## backend/app/ai

| Module | Provides |
|---|---|
| `contracts.py` | `ReviewInputs`, `ReviewReport` and its section models (`PatientFacts`: name, age, sex, `birth_date`), `ReviewOutcome`, `ModelClient`, `ModelReply` |
| `review.py` | `review_note(client, inputs)`, `PROMPT_VERSION` |
| `errors.py` | `ModelError`, `ModelNotConfigured`, `ModelUnavailable`, `ModelRequestRejected`, `ModelRefused` |
| `json_text.py` | `extract_json`, `parse_json_loose`, `render_json_template` |
| `schema.py` | response schemas sent with each call |
| `cdi.py`, `audit.py`, `mips.py` | CDI, audit checklist and MIPS section models (ChartMate field names); MIPS `MeasureStatus` |
| `hcc.py` | `HccScanOutput` (suspected conditions from the model), `HccReview` (stored, with the payment year), `hcc_review` |
| `prompts/cdi.py` | `COMPLIANT_QUERY_RULES`, the AHIMA/ACDIS query rules every provider question follows |
| `prompts/context.py` | `CONTEXT_HEADING`, `labelled_addendum(revision, text)` (how an addendum is shown to the model; used by the analysis and evaluation runs), `ADDENDUM_HEADING_PATTERN` (finds that label in note text) |
| `prompts/` | one module per section, plus the shared frame and context |

## backend/app/adapters

| Module | Provides |
|---|---|
| `object_store.py` | `ObjectStore` protocol (`put`, `get`, `signed_url`, `delete`, `delete_prefix` refusing anything that is not a folder), `S3ObjectStore` (S3 and R2; `client=` for a stubbed client), key builders `note_document_key`, `note_document_revision_key`, `analysis_response_key`, `evaluation_response_key(practice_id, run_id, case_id, attempt)`, `practice_prefix`, `note_prefix` |
| `object_listing.py` | `ListingStore` protocol (an `ObjectStore` with `list_keys(prefix)`, `object_pages(prefix)` yielding one list of `StoredObject` (key, `LastModified`) per S3 page, and `list_folders(prefix)` (the folders directly under it); folders only), `S3ListingStore` (an `S3ObjectStore` that also lists) |
| `messenger.py` | `Messenger` protocol, `build_messenger` (email: SES, SMTP or outbox; texts: SNS, Twilio or outbox), `OutboxMessenger` |
| `email_senders.py`, `sms_senders.py` | `SesEmail`, `SmtpEmail`, `SnsSms` (transactional, from `SNS_ORIGINATION_NUMBER` when set: `message_attributes`), `TwilioSms` |
| `mail_layout.py` | `html_from_text` (the HTML version of every email) |
| `pdf_text.py` | `read_pdf_text`, `DocumentUnreadable` |
| `pdf_writer.py` | `render_pdf(PdfDocument) -> bytes` (reportlab, Helvetica, page footer), blocks `PdfHeading`, `PdfText` (`body`, `secondary`, `quote`, `label`), `PdfFacts`, `PdfTable` (`weights`), `PdfPageBreak` |
| `gemini.py` | `GeminiClient` (the `ModelClient` for Gemini on the Developer API or Vertex AI, `GEMINI_BACKEND`), `VERTEX_PDF_TOO_LARGE` |
| `demo_model.py`, `demo_answers.py` | `DemoModelClient(DemoCodeBook)` (the `ModelClient` for `GEMINI_BACKEND=demo`: canned review bundles, model `DEMO_MODEL`), `demo_outcome(document)` (first SHA-256 byte modulo five over `DEMO_OUTCOMES`), `read_request(prompt, pdf)`; `DemoCodeBook` takes `em_ladder` and an ICD-10-CM describer from the worker, as adapters do not import `codes` |
| `oidc_providers.py` | the sign-in service registry `PROVIDERS` (`GOOGLE`, `MICROSOFT`, `YAHOO` as `ProviderSpec`: discovery address, algorithms, required claims, issuer rule, email-trust rule, settings names), `PROVIDER_NAMES`, `provider_label(name)`, `tenant_allowed(tenant, tid)`, `display_name(claims)`, `IdentityRefused`, `UnverifiedEmail`, `ProviderUnreachable` |
| `oidc.py` | `IdentityProvider` protocol, `OidcProvider` (one OpenID Connect client: discovery, PKCE S256, code exchange, `identity_from(id_token, nonce=)`), `ProviderIdentity` (provider, subject, email, name), `ProviderConfig`, `Endpoints`, `callback_url(site_url, provider)` (the redirect URI, passed to `authorization_url` and `identity` per sign-in), `endpoints_from(document)` (https endpoints only), `build_identity_providers(settings)`, `pkce_challenge` |
| `billing_contract.py` | the payment processor contract: `BillingProvider` protocol (`checkout_url`, `manage_url`, `cancel_at_period_end`, `set_quantity`, `read_event`, `subscription`), `CheckoutRequest`, `SubscriptionRef`, `ProcessorEvent`, `ProcessorSubscription` (status in the stored vocabulary), `WebhookRefused` (400), `BillingUnavailable` (503, fixed message), `PAYMENT_SUCCEEDED`, `PAYMENT_FAILED` |
| `stripe_billing.py` | `StripeBilling(api, webhook_secret=)` (Checkout sessions, Billing Portal, item quantity with prorations, `Stripe-Signature` checked on the raw body), `StripeSdk` (the `StripeApi` binding over the official SDK, async through httpx; Stripe errors become `BillingUnavailable`), `checkout_params`, `subscription_state` (period end from the subscription item), `event_subscription_id`, `STRIPE_STATUSES`, `HANDLED_EVENTS` |
| `paypal_billing.py` | `PayPalBilling(PayPalConfig, httpx.AsyncClient)` (REST API with a cached OAuth token; subscriptions, cancel, revise; webhooks verified through `verify-webhook-signature`), `paypal_client(environment)`, `checkout_body`, `subscription_state`, `event_subscription_id`, `PAYPAL_STATUSES`, `HANDLED_EVENTS`, `API_HOSTS` |
| `billing_providers.py` | `build_billing_providers(settings)` (a processor is built only when its credentials are set), `PROVIDER_NAMES` |

## backend/app/services (shared by several routes)

| Module | Provides |
|---|---|
| `finding.py` | `Finding`, `CODE_CHANGE_ACTIONS`, `SEVERE_AUDIT` (also importable from `findings.py`) |
| `findings.py` | `build_findings`, `visit_findings` |
| `code_additions.py` | `modifier_findings`, `add_on_findings`, `visit_code` |
| `risk_adjustment.py` | `risk_adjustment_findings(report, billed, icd, model)` (HCC age from the birth date on 1 February of the payment year, else the note's age with `age_from` `note`) |
| `routing.py` | `place(..., billed_diagnoses=)`, `has_diagnosis_codes`, `claim` (keeps units), `choices_for`, `open_questions` |
| `estimates.py` | `claim_estimate(codes, place_code, service_date)`, `claim_amount`, `estimate_difference`, `note_estimate`, `money` (Medicare national estimates) |
| `placement.py` | `current_findings`, `current_decisions`, `refresh_placement` |
| `analysis.py` | `request_analysis`, `claim_next`, `run_analysis`, `next_revision`, `latest_codes` |
| `audit_log.py` | `record_access`, `record_provider_access`, `record_system_access(db, actor, practice_id, action, note_id=, detail=)` for a `SystemActor` (id and name; written as kind `user`), `record_activity`, `record_sign_in` |
| `auth.py` | `sign_in_user` (the one sign-in policy), `start_session`, `end_all_sessions`, `issue_user_token` |
| `identity_sign_in.py` | `start(provider, site)`, `finish(db, provider, returned, site, ip=, agent=)` (tokens, a two-step challenge, or the `ProviderIdentity` to sign up), `bind_identity(db, user, provider, subject)` (one subject per user and provider, one user per subject in the user's realm), `SignInRefused` (`reason`) |
| `account_lookup.py` | `account_by_email(db, email, realms)` (the one account with that email in those realms, or None when there is none or more than one), `email_in_use(db, email, realm)` (in `account_space(realm)`), `normal_email` |
| `signup.py` | `signup_options(settings, site)`, `ensure_signup_here(site)` (404 off the practice site), `check_email_signup` (open, agreement, time zone, rate limits), `request_email_signup(db, messenger, form, ip=, agent=)` (the background half: existing-account email or trial practice and invite), `identity_token`, `pending_identity(token)`, `complete_identity_signup(db, token, form, visitor)`, `EmailSignup`, `IdentitySignup`, `Visitor` |
| `practice_accounts.py` | `add_practice_with_admin(db, PracticeDraft, AdminDraft) -> NewPractice` (used by HQ and self sign-up), `signup_source(practice)`, `SIGNUP_SOURCES` |
| `plans.py` | `CATALOG` (immutable; `PlanTerms`: name, pricing `free`, `per_provider` or `custom`, cents per provider a month and a year, `max_users`, `max_providers`, `self_checkout`), `PLAN_KEYS`, `CHECKOUT_PLANS`, `PRICINGS`, `plan_terms(key)`, `price_cents(terms, interval, providers)`, `annual_months_free(terms)`, `price_id(settings, provider, plan, interval)`, `plan_for_price`, `prices_complete`, `PRICE_SETTING_PREFIX` |
| `plan_limits.py` | `ensure_user_room(db, practice)`, `ensure_provider_room(db, practice, adding)` (409 naming the plan and limit), `user_limit(practice, subscription)` (the plan's, and seats while no subscription is live), `provider_limit`, `subscription_for(db, practice_id, lock=)`, `is_live`, `LIVE_STATUSES`, `active_provider_count`, `user_count` |
| `subscriptions.py` | `plan_catalog`, `offered_providers(providers, settings)`, `plan_overview(db, practice)`, `standing`, `start_checkout(db, actor, providers, CheckoutChoice)`, `manage_link`, `cancel_subscription`, `subscription_ref(row)`, `refuse_manual_change(subscription)` (HQ's plan and renewal edits while a subscription is live), `STANDINGS`, `MANAGED_BY`, `PROVIDER_LABELS` |
| `subscription_events.py` | `receive_webhook(db, provider, body, headers)` (verify, record once, fetch, apply, commit), `apply_subscription(db, provider_name, state, payment=, now=)` (the status-to-access rules), `access_until(row, zone, grace_days)` |
| `quantity_sync.py` | `sync_quantities(db, providers, practice_id=)` (live subscriptions to `max(1, active providers)`; a processor failure waits for the next run) |
| `rate_limits.py` | `RateRule`, `hit(db, rule, key)`, the rules (`LOGIN_PER_EMAIL`, `IDENTITY_PER_IP`, `SIGNUP_PER_IP`, `SIGNUP_PER_EMAIL` and the rest) |
| `two_step.py` | `enrol_secret`, `accept_code` (replay-safe, re-encrypts legacy secrets), `forget_two_step` |
| `recovery_codes.py` | `replace_recovery_codes`, `use_recovery_code`, `clear_recovery_codes`, `remaining_recovery_codes` |
| `password_reset.py` | `send_reset_email` (used by forgot password, Team and HQ; the link follows `realm_url`) |
| `team.py` | `send_invite(db, messenger, user, team_name=)` (the set-password invite for practice and HQ accounts; the link follows `realm_url`), `EMAIL_TAKEN` |
| `hq_team.py` | `hq_team`, `invite_hq_member`, `resend_hq_invite`, `deactivate_hq_member` (refuses yourself and the last active HQ account), `reactivate_hq_member`, `enrol_hq_person` (the `invite_hq` script: invite, resend, rename or leave alone) -> `HqEnrolment` |
| `note_texts.py` | `note_texts(db, note_id)`, `current_texts(texts)` (from the latest `document` revision onward; used by the analysis and the note view) |
| `uploads.py` | `check_pdf(name, data)` (PDF signature and size), `create_upload` (a person), `create_intake_upload(db, store, practice, plan, files)` (source `intake`, no user, access entry by `INTAKE_ACTOR` Bodha intake), `batch_history` (Intake as the uploader of intake batches) |
| `records.py` | `replace_document`, `NewDocument`, `access_log_page`, `retention_cutoff(now, zone, years)`, `purge_access_logs(db, now) -> int`, `delete_practice`, `PRACTICE_DELETED` |
| `file_sweep.py` | `sweep_orphan_files(db, store, now) -> int` (the daily orphan sweep; a `ListingStore`), `classify_key(practice_id, key) -> StoredFile` (document, reply, remittance, evaluation, intake or unknown), `ORPHAN_AGE` (24 hours) |
| `provider_details.py` | `validated_details`, `details_view`, `DETAIL_FIELDS` (provider credentialing) |
| `provider_channels.py` | how provider questions travel: `require_channel(provider, channel)` (409 `TEXTS_UNAVAILABLE` for a text while `can_send_texts` is false; 422 when the provider has no address for the channel), `usable_channel(preferred, name=, email=)` (a preferred text becomes email while texts cannot be sent; 422 naming a provider with no email), `contact_for`, `CHANNELS`, `CONTACT_FIELDS`, `EMAIL`, `TEXT` |
| `payers.py` | `payer_list`, `has_active_payer`, `add_payer`, `change_payer`, `remove_payer`, `PLAN_TYPES` |
| `worklists.py` | `queue_query(..., assigned=)` (`UNASSIGNED` for none), `queue_rows`, `lane_counts(db, practice_id, now=)`, `summary`, `user_names`, `assignee_name`, `QUEUE_STATUSES`, `DUE_SOON` |
| `assignment.py` | `assign_notes(db, actor, note_ids, user_id)` (the assignment rules; records `assigned`) |
| `digests.py` | `send_due_digests(db, messenger, now)`, `digest_text`, `set_digest_preference` |
| `search.py` | `search_notes(db, actor, text)`, `code_forms(term)` |
| `x12.py` | `read_transactions(text, code=)` (strict X12 envelope: separators from ISA, nesting, control numbers and counts), `Segment.get / required / parts`, `Transaction`, `X12Invalid` (422) |
| `remittance_835.py` | `parse_835(data) -> list[PaymentAdvice]` (balanced lines and payments), `PaymentAdvice`, `ClaimPayment.payments()`, `ServicePayment`, `Adjustment` (`as_json` / `from_json`) |
| `remittance_outcomes.py` | `line_outcome(line, claim_status)`, `is_downcode(billed, paid)`, `plan_type_for(filing_indicator, listed)`, `appeal_days(stored)`, `appeal_deadline(remitted_on, plan_type, days)`, `line_appeal_by(remitted_on, plan_type, stored, days)` (the current window when the line has a plan type, else its stored date), `validated_appeal_days`, `DEFAULT_APPEAL_DAYS`, `APPEALABLE`, the status names |
| `remittance_matching.py` | `matching_note(db, practice_id, claim, line)`, `same_person(a, b)`, `name_tokens` |
| `appeal_letters.py` | `appeal_letter(AppealFacts) -> str`, `money_text(cents)` |
| `remittances.py`, `remittance_views.py` | `upload_remittance`, `remittance_key`, `listed_plan_type`; `remittance_page`, `remittance_detail`, `appeal_draft`, `stored_appeal_days`, `save_appeal_days`, `defense_packet_path` |
| `intake_settings.py`, `intake.py` | `intake_config`, `intake_view`, `save_intake`, `inbox_prefix`, `IntakeConfig`, `INBOX_NAME`; `poll_intake(db, store, now) -> int`, `sort_inbox(inbox, keys, config, today)`, `arrival_name(name, data)` (the checksum name a dropped file gets) |
| `query_governance.py` | `repeat_query_blocked(db, note, keys)`, `refuse_repeat_queries`, `escalate_unanswered(db, messenger, now) -> int`, `escalation_text`, `addendum_export`, `labelled_addendum`, `ASKED_STATUSES` (no import of `addenda`, which calls it) |
| `query_metrics.py` | `query_metrics(db, practice_id, days=, now=)`, `metrics_for(notes, requests)`, `AskedRequest`, `QueryMetrics`, `NOT_AGREED` |
| `addenda.py` | `create_request`, `send_link`, `send_code`, `verify_code`, `provider_request`, `other_requests`, `switch_request`, `answer`, `addendum_text` |
| `visit_levels.py` | `visit_codes(db, note_ids)` (the E/M code of the final code set once approved, otherwise of the latest billed set), `visit_code(codes)`, `is_leveled(code)` (families of three or more levels), `is_top_level(code)` (the two highest levels) |
| `claim_checks.py` | `claim_checks(db, actor, note_id)` (NCCI edits and payer flags for the note's current claim, with `initial_visit_repeated` from the patient's other notes; records `checked claim edits`), `edits_for(tables, codes, note)`, `stay_history(db, note)` (the same patient's earlier notes as `EarlierVisit`s) |
| `claim_lines.py` | `claim_lines(db, actor, note_ids)` (approved, not exported; records `built claim lines`), `build_claim(party, codes, primaries=)` (diagnosis letters A to L, at most 12; stored pointers as letters), `line_pointers(codes, primaries)` (stored, else an add-on's primary's, else the first four), `add_on_primaries(tables, codes, service_date)` (NCCI add-on to its primary on the claim), `note_pointers(db, actor, note_id)` and `pointers_view` (the pointer editor's data), `claims_json`, `claims_csv` (formula-safe), `billing_npi(npi, details)`, `CLAIM_LINE_COLUMNS` |
| `review_actions.py` | `current_claim(db, note)` (billed codes, latest decisions and stored pointers), `stored_pointers(db, note_id)`, `save_pointers(db, actor, note_id, lines)` (records `linked diagnoses`), `approve`, `reopen`, `reopen_many(db, actor, note_ids)` (undoes approvals together or not at all; records `reopened`), `note_for` and the other review actions; a compliance decision's reason is written to the access log (`compliance keep`, `compliance confirm`) |
| `agreement.py` | `ClaimElements` (E/M code, ICD-10 set, modifier set), `elements_of(codes)`, `elements_from_json`, `em_level(code)` (MDM level or `Time`), `em_direction`, `compare_elements(reference, compared)` (one note), `summarize(comparisons)` (Wilson rates for per-note elements, per-note bootstrap for ICD-10 precision and recall), `visit_agreement(comparisons)` (E/M exact rate) |
| `code_sets.py` | `latest_codes(db, note_id, kind)`, `latest_codes_for(db, kind, note_ids) -> dict[note id, codes]` (the latest set of each note in one query; used by `insights` and `visit_levels`), `next_revision(db, model, note_id, **filters)` (the same queries as `analysis.py`, which should import them from here) |
| `autonomy.py` | `provider_eligibility(db, provider) -> Eligibility` (latest `done` audit run), `MIN_AUDIT_NOTES`, `MIN_EM_LOWER_BOUND`, `MAX_BODHA_HIGHER_SHARE` |
| `audit_samples.py` | `draw_sample(db, actor, SampleRequest) -> run id` (one `audit_runs` row, one `audit_samples` row per note), `run_items(db, practice_id, run_id)`, `samples_overview`, `sample_results`, `reference_elements` |
| `blind_review.py` | `next_item`, `submit_answer` (closes the run with its last item), `refuse_blind_note(db, actor, note_id)` (403 `BLIND_NOTE` while the caller has an open item for the note; the routes use it through `api/blinding.SightedReader` and `SightedDecider`) |
| `auto_approval.py` | `auto_approve_eligible(db, note)`, `auto_approve(db, note)` (caller commits), `held_for_quality_check(note_id)`; imports only `placement` as a module and lower layers, so `placement`, `analysis` and `review_actions` can call it |

## backend/app/api/responses

One module per area; each route names its model with `response_model=`. Services keep returning
dictionaries and the model validates them (see Architecture, API types).

| Module | Provides |
|---|---|
| `view.py` | `View` (base model, `extra="forbid"`) |
| `errors.py` | `ErrorResponse` (`error`, `message`), `error_responses(path, endpoint, dependencies)` (the error responses a route can return, read from its dependency tree) |
| `base.py` | re-exports `View` and `ErrorResponse`; `ExactRoute` (the `route_class` of every router: responses carry exactly the keys the service built, and errors are described by `error_responses`), `Omittable[T]` (a key a service may leave out: optional, never `null`, declared `= None`), `file_download(media_type)` (route options for a file response), `Created` (`id`), `DocumentLink` (`url`), the shared literals `NoteStatus`, `Lane`, `Role`, `PracticeRole`, `Channel`, `TextSource`, `RequestStatus`, `PlanType` (derived from the model and service constants) |
| `auth.py` | `User`, `PracticeSummary` (`can_send_texts` tells screens whether to offer texts), `Checks`, `SignedIn` (`recovery_codes` omittable), `MfaChallenge`, `MfaEnrolment`, `SignInProviders` (`providers`, `signup`), `SignUpOptions`, `IdentityProviderName`, `SignedInDevice`, `RecoveryCodeStatus`, `RecoveryCodes`, `Preferences` |
| `work.py` | `NoteSummary`, `QueueRow`, `ComplianceRow`, `LaneCount`, `LaneCounts`, `BatchProgress`, `TodaySummary`, `QueuePage`, `SearchResults`, `ComplianceList`, `LaneReason`, `EmAction` |
| `notes.py` | `NoteDetail` and its parts (`NoteHeader`, `TextRevision`, `NoteText`, `AnalysisView`, `Finding`, `FindingAction`, `ClaimEstimates`, `NoteHistory`, `CodeJson` (`units` and `pointers` omittable), `AddendumRequestView`, `AddendumQuestion`, `AddendumAnswer`) |
| `note_actions.py` | results of note actions (`NoteState`, `NoteLane`, `ComplianceOutcome`, `ApprovedNotes`, `AssignedNotes`, `DeletedNotes`, `QueuedNotes`, `NotePayer`, `RequestCancelled`, `RequestCreated`) and `ClaimPointers` |
| `claims.py` | `ClaimChecks` (`ClaimEdit`: `PtpEdit`, `MueEdit`, `AocEdit` discriminated by `kind`; `PayerFlag` with `earlier` omittable), `ClaimLinesExport` |
| `uploads.py`, `billing.py`, `practice.py`, `team.py`, `hq.py`, `respond.py` | the upload, billing, practice setup (with `IntakeView`), team, HQ and provider-request views |
| `insights.py`, `defensibility.py` | `Insights`, `EmMix`, `QueryMetricsReport`; `NoteDay`, `FlaggedDays` (`from`, `to` by alias) |
| `quality.py`, `training.py`, `evaluations.py` | `Rate`, `AgreementSummary`, `ElementComparison`, `ClaimElements`, sample, autonomy and level-mix views; blind review and training views; evaluation runs (`EvalSummary` all omittable, as a queued run stores `{}`) |
| `health.py` | `Health`, `Readiness`, `PASSED`, `FAILED` |
| `signup.py` | `PendingIdentity` (email, name, provider) |
| `plan.py` | `PlanCatalog`, `PlanTerms`, `PlanStatus`, `PlanSubscription`, `RedirectLink`, `BillingProviderName`, `BillingInterval` |

## frontend/src (shared)

| Module | Provides |
|---|---|
| `components/shared/shortcuts/registry.ts` | `SHORTCUTS` (the one list of keyboard shortcuts, by scope `global`, `today`, `queue`, `review`: `n` starts reviewing on Today; `y` and `n` accept or reject the selected finding, `q` (or `p`) asks the provider, `u` undoes the last toast action), `comboFor`, `shortcutsIn(scope, role)`, `scopeForPath`, `isTyping`, `comboKeys`, `shortcutKeys(id, mac)` (`A`, `⌘+K`), `shortcutTitle(id, mac)` (`Previous note (K)`, for buttons and key hints) |
| `components/shared/shortcuts/useIsMac.ts` | `useIsMac()` (Command or Ctrl in key labels) |
| `components/shared/shortcuts/useShortcuts.ts` | `useShortcuts(scope, handlers)` (ignores plain keys while typing and while a dialog is open; listens from the first paint) |
| `components/shared/toast/` | `showToast(message, action?)`, `dismissToast`, `runToastAction`, `useToast`, `TOAST_SECONDS`; `ToastHost` (in the practice layout; `u` runs the action). Undo for reversible actions instead of a confirmation |
| `components/shared/noteDetail.ts` | `useNoteDetail(noteId)`, `prefetchNoteDetail(noteId)`, `forgetNoteDetail(noteId)` (one cache key for a note's detail across note review, compliance and Today) |
| `components/shared/shortcuts/ShortcutList.tsx`, `ShortcutsDialog.tsx` | the shortcut list (help page and the `?` dialog) |
| `components/shared/overlays.ts` | `openOverlay("search" \| "shortcuts")`, `closeOverlay`, `useOpenOverlay` |
| `components/shared/noteStatus.ts` | `noteStatus`, `DELETABLE_STATUSES`, `ASSIGNABLE_STATUSES` |
| `hooks/useAssignees.ts` | `useAssignees(user)` (who the user may assign notes to) |
| `hooks/useRemote.ts` | `useRemote(key, load, keepSeconds = 0)` (loading, error and success; serves a fresh cached or prefetched value at once and shares a request already running for the key) |
| `hooks/remoteCache.ts` | `prefetchRemote(key, load)` (kept `PREFETCH_SECONDS`), `loadRemote`, `readRemote`, `keepRemote`, `writeRemote`, `editRemote`, `forgetRemote`, `LOOKUP_SECONDS` (places, payers, providers); emptied when the session ends |
| `hooks/useRememberedParams.ts` | `useRememberedParams(screen, keys)` (restores a screen's last filters per user from local storage when it opens without any; never the search text), `rememberedParams` |
| `components/ui/RadioOption.tsx` | `RadioOption` (a native radio drawn as a bordered option row: focus ring, checked ring), `OPTION_CARD` (the checked and focus rings for a larger card holding a radio) |
| `components/shared/plan-cards/` | `PlanCard` (a plan's name, price for the period and limits, with an action slot; used by `/plan` and `/pricing`), `IntervalControl` (Monthly or Annual with the months a year saves), `cardPrice`, `limitLines`, `mostMonthsFree`, `PLAN_CARD_TEXT` |
| `components/shared/InviteDialog.tsx` | `InviteDialog` (name and email with checks, a slot for more fields, and the send action; practice Team and HQ Team) |
| `components/shared/MemberCells.tsx` | `MemberIdentity` (avatar, name, "You", email), `MemberTwoStep`, `MemberLastSeen` (a team member's cells on practice Team and HQ Team) |
| `components/shared/plan-banner/` | `PlanBanner` (admins: trial days left or a failed payment, linking to `/plan`, hidden for the day once dismissed), `bannerFor(status)` |
| `lib/roles.ts` | `canUse(role, area)` and `canDo(role, action)` (mirror the route guards), `canReach(user, area)` and `canSearch(user)` (the same, closed to a billing-only session except the plan area), `canOpenPath(user, pathname)` (a billing-only session opens only `/plan`), `homeFor(user)` (`/plan` while billing-only), `PLAN_PATH`, `idleMinutesFor` |
| `lib/site.ts` | `siteUrl()` (`SITE_URL`, the main host), `adminUrl()` (`ADMIN_URL` or null; read at request time by `src/proxy.ts` to keep `/hq` on the HQ host) |
| `lib/backend.ts`, `lib/api/planCatalogServer.ts` | `backendUrl()` (`BACKEND_URL`, else `LOCAL_BACKEND_URL`; read by the `next.config.ts` rewrites and by server-side fetches), `loadPlanCatalog()` (server only: `GET /api/plans` at the backend, kept `PLAN_CATALOG_REVALIDATE_SECONDS` (an hour), `null` when the backend cannot be reached or answers an error) |
| `hooks/usePlanStatus.ts`, `hooks/usePlanCatalog.ts` | `usePlanStatus(enabled)` (`GET /api/plan`, cached a minute; shared by the banner and the plan screen), `usePlanCatalog()` (`GET /api/plans`), `PLAN_STATUS_KEY`, `PLAN_CATALOG_KEY` |
| `components/ui/PasswordInput.tsx` | `PasswordInput` (every password field: a show or hide button inside the field with `aria-pressed`; focus stays in the field; `look` `boxed` or `bare`) |
| `components/shared/sign-in-providers/` | `ProviderButtons` ("Continue with …" for each enabled service), `ProviderMark` (inline Google, Microsoft and Yahoo marks), `providerName` |
| `hooks/useSignInOptions.ts` | `useSignInOptions()` (`GET /api/auth/providers`), `loadedOptions` |
| `hooks/useCanSendTexts.ts`, `lib/channels.ts` | `useCanSendTexts()` (the signed-in practice's `can_send_texts`), `isOfferedChannel(channel, canSendTexts)`, `usableChannel(preferred, canSendTexts)` (email while texts cannot be sent; used by asking a provider and the provider form and table) |
| `lib/timeZones.ts` | `TIME_ZONE_LABELS`, `TIME_ZONES`, `DEFAULT_TIME_ZONE`, `zoneOptions(current)`, `preferredTimeZone(detected)` (the browser's zone when listed, else Central) |
| `components/ui/Skeleton.tsx` | `SkeletonFrame` (a `status` region with the loading label), `SkeletonBlock` |
| `components/ui/Pager.tsx` | `Pager` (offset pages with a total; text from `SHARED_TEXT.pager`), `offsetFrom(param)` |
| `components/ui/Select.tsx` | `Select` (the one single-choice control; options `{ value, label, disabled?, tone?, group? }` as `SelectOption`, `onChange(value)`, `label` when no `Field` labels it, `variant` `field`, `filter` or `inline`, `name` for forms; takes `id` and the ARIA props from `Field`; a search box above twelve options). Input's native `Select` remains only for `features/sign-up` ([0027](decisions/0027-own-select-and-date-picker.md)) |
| `components/ui/DatePicker.tsx`, `DateRange.tsx` | `DatePicker` (an ISO day or `null` in and out; `min`, `max`, `today`, `label`, `variant` `field` or `filter`; typed days checked when the field loses focus), `DateRange` (two labelled pickers, each limited by the other) |
| `components/ui/useFloating.ts`, `floating.ts` | `useFloating(anchor, panel, align)` (a fixed panel below its anchor or above it when there is no room; follows scrolling, closes on an outside click; used by `Select`, `DatePicker` and `MenuButton`), `floatingStyle` |
| `components/ui/fieldStyles.ts`, `strings.ts` | `FIELD_CLASSES`, `FILTER_CLASSES` (field and compact filter shapes with their focus and error rings; `Input` exports `CONTROL`, the full-width field); `UI_TEXT` (the words the generic controls show) |
| `components/shared/batchProgress.ts` | `batchCounts(batch)` (total, finished, pending, failed from counts by status) |
| `components/shared/blind-coding/` | `BlindCodingPanel` (note text, PDF button and the blind form; renders nothing else of the note), `BlindCodingForm`, `parseAnswer`, `splitCodes`, `useBlindSession(sampleId)` (audits and training) |
| `components/shared/rates.ts` | `formatRate` (`50% (9.5%–90.5%)`), `formatInterval`, `formatCounted` for a `Rate` with its 95% interval (Wilson or bootstrap) |
| `lib/api/types.ts` | the API types screens import: aliases over the generated `components["schemas"]` and literal unions derived from them, plus the query and form types the client composes |
| `lib/api/schema.ts` | generated by `npm run api:types` from `openapi.json`; never edited by hand |
| `lib/format.ts` | `formatWholeDollars(cents)` (plan prices, `$1,490`), `formatCalendarDay(isoDate \| null, style)` (`—` for null; `complete` spells the whole day), `parseCalendarDay(text)` (day first, ISO or `27 Nov 2026`; `null` when it cannot be read), `formatMonthYear`, `MONTH_NAMES`, `WEEKDAY_NAMES` and `WEEK_STARTS_ON` (Monday, as en-GB), `formatPercent`, `formatMoney`, `formatMinutes`, `formatDueIn`, `formatSince` and the other shared formatters |
| `lib/dates.ts` | `parseIsoDate`, `toIsoDate`, `isIsoDate`, `localIsoDate`, `isoDateInZone`, `addDays`, `addMonths` (keeps the day where the month allows), `dayInMonth`, `daysInMonth`, `weekdayOf`, `clampIsoDate`, `isWithin`, `monthWeeks(year, month, weekStartsOn)` |
