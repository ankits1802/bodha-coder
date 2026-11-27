# Shared components

Check here before writing a helper.

## backend/app/core

| Module | Provides |
|---|---|
| `config.py` | `Settings`, `get_settings()` |
| `db.py` | `engine`, `SessionFactory`, `get_session` |
| `security.py` | `hash_password`, `verify_password`, `issue_token`, `read_token`, `digest`, `same_digest`, `random_token`, `random_code`, TOTP helpers (`mfa_step_for`, `mfa_uri`, `new_mfa_secret`), `seal_mfa_secret` / `open_mfa_secret` / `is_sealed_mfa_secret` (Fernet, `MFA_ENCRYPTION_KEY`), `MfaKeyUnavailable` |
| `errors.py` | `AppError` and `Unauthorized`, `Forbidden`, `NotFound`, `Conflict`, `Invalid`, `Unavailable`, `RateLimited` (429) |
| `roles.py` | role groups used by every route guard |
| `calendar.py` | `zone_named`, `day_bounds`, `today_in` (practice calendar days), `shift_years(day, years)` (29 February becomes the 28th in a common year) |
| `deps.py` | `Db`, `Actor`, `current_actor`, `require(*roles)`, `ProviderActor`, `current_provider`, `ensure_practice_open`, `PlanEnded` |
| `chi_square.py` | `chi_square_sf(statistic, degrees_of_freedom)` (closed forms for whole degrees of freedom), `pooled_cells(observed, expected, minimum=5)`, `goodness_of_fit(observed, expected) -> GoodnessOfFit \| None` (None when fewer than two pooled cells) |
| `statistics.py` | `wilson(successes, trials) -> Rate` (Wilson score 95% interval; `Rate.value/low/high` are None with no trials), `bootstrap_ratio(units, *, resamples=2000, seed=BOOTSTRAP_SEED) -> Rate` (ratio of summed parts to summed wholes with a percentile 95% interval from resampling the units, the unit of independence, with replacement; nearest rank, resamples with an empty denominator left out), `f1_score(precision, recall)`, `chi_square_homogeneity(first, second) -> ChiSquare \| None` (two periods over ordered levels, sparse levels pooled through `chi_square.pooled_cells`), `Z_95` |
| `logging.py` | `configure_logging()` (JSON lines on stdout for every process, uvicorn's access log off), `JsonFormatter` (adds the request id; exceptions as type, frames and cause types, never their message), `RequestLog` (ASGI middleware: one `bodha.access` line per request with method, route template, status, duration and request id; `X-Request-ID` in and out), `log_queue_metrics(logger, *, queued, running, at)` (CloudWatch Embedded Metric Format line, namespace `BodhaCoder`) |

## backend/app/codes

| Module | Provides |
|---|---|
| `icd.py` | `load_catalog()`, `IcdCatalog.for_service_date`, `IcdRelease.get / more_specific / is_unspecified`, `format_icd`, `fiscal_year_for` |
| `em.py` | `EM_FAMILIES` (each `EmFamily` with its levels and add-ons, such as 99292), `compare_em`, `describe_em`, `is_em_code` |
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
| `prompts/` | one module per section, plus the shared frame and context |

## backend/app/adapters

| Module | Provides |
|---|---|
| `object_store.py` | `ObjectStore` protocol (`put`, `get`, `signed_url`, `delete`, `delete_prefix` refusing anything that is not a folder), `S3ObjectStore` (S3 and R2; `client=` for a stubbed client), key builders `note_document_key`, `note_document_revision_key`, `analysis_response_key`, `evaluation_response_key(practice_id, run_id, case_id, attempt)`, `practice_prefix`, `note_prefix` |
| `object_listing.py` | `ListingStore` protocol (an `ObjectStore` with `list_keys(prefix)`, `object_pages(prefix)` yielding one list of `StoredObject` (key, `LastModified`) per S3 page, and `list_folders(prefix)` (the folders directly under it); folders only), `S3ListingStore` (an `S3ObjectStore` that also lists) |
| `messenger.py` | `Messenger` protocol, `build_messenger` (email: SES, SMTP or outbox; texts: SNS, Twilio or outbox), `OutboxMessenger` |
| `email_senders.py`, `sms_senders.py` | `SesEmail`, `SmtpEmail`, `SnsSms`, `TwilioSms` |
| `mail_layout.py` | `html_from_text` (the HTML version of every email) |
| `pdf_text.py` | `read_pdf_text`, `DocumentUnreadable` |
| `pdf_writer.py` | `render_pdf(PdfDocument) -> bytes` (reportlab, Helvetica, page footer), blocks `PdfHeading`, `PdfText` (`body`, `secondary`, `quote`, `label`), `PdfFacts`, `PdfTable` (`weights`), `PdfPageBreak` |
| `gemini.py` | `GeminiClient` (the `ModelClient` for Gemini on the Developer API or Vertex AI, `GEMINI_BACKEND`), `VERTEX_PDF_TOO_LARGE` |
| `google_oidc.py` | `GoogleSignIn` protocol, `GoogleOidc`, `build_google_sign_in`, `GoogleIdentity`, `GoogleRefused`, `GoogleUnreachable`, `pkce_challenge` |

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
| `rate_limits.py` | `RateRule`, `hit(db, rule, key)`, the rules (`LOGIN_PER_EMAIL` and the rest) |
| `two_step.py` | `enrol_secret`, `accept_code` (replay-safe, re-encrypts legacy secrets), `forget_two_step` |
| `recovery_codes.py` | `replace_recovery_codes`, `use_recovery_code`, `clear_recovery_codes`, `remaining_recovery_codes` |
| `password_reset.py` | `send_reset_email` (used by forgot password, Team and HQ) |
| `note_texts.py` | `note_texts(db, note_id)`, `current_texts(texts)` (from the latest `document` revision onward; used by the analysis and the note view) |
| `uploads.py` | `check_pdf(name, data)` (PDF signature and size), `create_upload` (a person), `create_intake_upload(db, store, practice, plan, files)` (source `intake`, no user, access entry by `INTAKE_ACTOR` Bodha intake), `batch_history` (Intake as the uploader of intake batches) |
| `records.py` | `replace_document`, `NewDocument`, `access_log_page`, `retention_cutoff(now, zone, years)`, `purge_access_logs(db, now) -> int`, `delete_practice`, `PRACTICE_DELETED` |
| `file_sweep.py` | `sweep_orphan_files(db, store, now) -> int` (the daily orphan sweep; a `ListingStore`), `classify_key(practice_id, key) -> StoredFile` (document, reply, remittance, evaluation, intake or unknown), `ORPHAN_AGE` (24 hours) |
| `provider_details.py` | `validated_details`, `details_view`, `DETAIL_FIELDS` (provider credentialing) |
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
| `review_actions.py` | `current_claim(db, note)` (billed codes, latest decisions and stored pointers), `stored_pointers(db, note_id)`, `save_pointers(db, actor, note_id, lines)` (records `linked diagnoses`), `approve`, `note_for` and the other review actions |
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
| `base.py` | `View` (base model, `extra="forbid"`), `ExactRoute` (the `route_class` of every router: responses carry exactly the keys the service built), `Omittable[T]` (a key a service may leave out: optional, never `null`, declared `= None`), `file_download(media_type)` (route options for a file response), `Created` (`id`), `DocumentLink` (`url`), the shared literals `NoteStatus`, `Lane`, `Role`, `PracticeRole`, `Channel`, `TextSource`, `RequestStatus`, `PlanType` (derived from the model and service constants) |
| `auth.py` | `User`, `PracticeSummary`, `Checks`, `SignedIn` (`recovery_codes` omittable), `MfaChallenge`, `MfaEnrolment`, `SignInProviders`, `SignedInDevice`, `RecoveryCodeStatus`, `RecoveryCodes`, `Preferences` |
| `work.py` | `NoteSummary`, `QueueRow`, `ComplianceRow`, `LaneCount`, `LaneCounts`, `BatchProgress`, `TodaySummary`, `QueuePage`, `SearchResults`, `ComplianceList`, `LaneReason`, `EmAction` |
| `notes.py` | `NoteDetail` and its parts (`NoteHeader`, `TextRevision`, `NoteText`, `AnalysisView`, `Finding`, `FindingAction`, `ClaimEstimates`, `NoteHistory`, `CodeJson` (`units` and `pointers` omittable), `AddendumRequestView`, `AddendumQuestion`, `AddendumAnswer`) |
| `note_actions.py` | results of note actions (`NoteState`, `NoteLane`, `ComplianceOutcome`, `ApprovedNotes`, `AssignedNotes`, `DeletedNotes`, `QueuedNotes`, `NotePayer`, `RequestCancelled`, `RequestCreated`) and `ClaimPointers` |
| `claims.py` | `ClaimChecks` (`ClaimEdit`: `PtpEdit`, `MueEdit`, `AocEdit` discriminated by `kind`; `PayerFlag` with `earlier` omittable), `ClaimLinesExport` |
| `uploads.py`, `billing.py`, `practice.py`, `team.py`, `hq.py`, `respond.py` | the upload, billing, practice setup (with `IntakeView`), team, HQ and provider-request views |
| `insights.py`, `defensibility.py` | `Insights`, `EmMix`, `QueryMetricsReport`; `NoteDay`, `FlaggedDays` (`from`, `to` by alias) |
| `quality.py`, `training.py`, `evaluations.py` | `Rate`, `AgreementSummary`, `ElementComparison`, `ClaimElements`, sample, autonomy and level-mix views; blind review and training views; evaluation runs (`EvalSummary` all omittable, as a queued run stores `{}`) |
| `health.py` | `Health`, `Readiness`, `PASSED`, `FAILED` |

## frontend/src (shared)

| Module | Provides |
|---|---|
| `components/shared/shortcuts/registry.ts` | `SHORTCUTS` (the one list of keyboard shortcuts, by scope `global`, `queue`, `review`), `comboFor`, `shortcutsIn(scope, role)`, `scopeForPath`, `isTyping`, `comboKeys`, `shortcutKeys(id, mac)` (`A`, `⌘+K`), `shortcutTitle(id, mac)` (`Previous note (K)`, for buttons and key hints) |
| `components/shared/shortcuts/useIsMac.ts` | `useIsMac()` (Command or Ctrl in key labels) |
| `components/shared/shortcuts/useShortcuts.ts` | `useShortcuts(scope, handlers)` (ignores plain keys while typing and while a dialog is open) |
| `components/shared/shortcuts/ShortcutList.tsx`, `ShortcutsDialog.tsx` | the shortcut list (help page and the `?` dialog) |
| `components/shared/overlays.ts` | `openOverlay("search" \| "shortcuts")`, `closeOverlay`, `useOpenOverlay` |
| `components/shared/noteStatus.ts` | `noteStatus`, `DELETABLE_STATUSES`, `ASSIGNABLE_STATUSES` |
| `hooks/useAssignees.ts` | `useAssignees(user)` (who the user may assign notes to) |
| `components/ui/Pager.tsx` | `Pager` (offset pages with a total; text from `SHARED_TEXT.pager`), `offsetFrom(param)` |
| `components/shared/batchProgress.ts` | `batchCounts(batch)` (total, finished, pending, failed from counts by status) |
| `components/shared/blind-coding/` | `BlindCodingPanel` (note text, PDF button and the blind form; renders nothing else of the note), `BlindCodingForm`, `parseAnswer`, `splitCodes`, `useBlindSession(sampleId)` (audits and training) |
| `components/shared/rates.ts` | `formatRate` (`50% (9.5%–90.5%)`), `formatInterval`, `formatCounted` for a `Rate` with its 95% interval (Wilson or bootstrap) |
| `lib/api/types.ts` | the API types screens import: aliases over the generated `components["schemas"]` and literal unions derived from them, plus the query and form types the client composes |
| `lib/api/schema.ts` | generated by `npm run api:types` from `openapi.json`; never edited by hand |
| `lib/format.ts` | `formatCalendarDay(isoDate \| null, style)` (`—` for null), `formatPercent`, `formatMoney`, `formatMinutes`, `formatDueIn`, `formatSince` and the other shared formatters |
