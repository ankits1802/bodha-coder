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
| `logging.py` | `configure_logging()` (JSON lines on stdout for every process, uvicorn's access log off), `JsonFormatter` (adds the request id; exceptions as type, frames and cause types, never their message), `RequestLog` (ASGI middleware: one `bodha.access` line per request with method, route template, status, duration and request id; `X-Request-ID` in and out), `log_queue_metrics(logger, *, queued, running, at)` (CloudWatch Embedded Metric Format line, namespace `BodhaCoder`) |

## backend/app/codes

| Module | Provides |
|---|---|
| `icd.py` | `load_catalog()`, `IcdCatalog.for_service_date`, `IcdRelease.get / more_specific / is_unspecified`, `format_icd`, `fiscal_year_for` |
| `em.py` | `EM_FAMILIES` (each `EmFamily` with its levels and add-ons, such as 99292), `compare_em`, `describe_em`, `is_em_code` |
| `modifiers.py` | `VISIT_MODIFIERS`, `PROCEDURE_MODIFIERS`, `allowed_modifiers(code)`, `modifier_meaning(code, modifier)` |
| `hcc.py` | `load_hcc_model(payment_year)`, `hcc_model_for(payment_year)` (None when not vendored), `HccModel.hccs_for / payment_hccs / score / label / factor / is_trumped`, `HccPatient`, `payment_year_for(service_date)`, `segment_for(age)`, `sex_code`, `HccDataCorrupt` (CMS-HCC V28, checksummed manifest) |
| `billing_codes.py` | `Code` (`units`, `label()` `96127 ×2`, `as_text()` `96127x2`, `as_json` / `from_json`), `InvalidUnits`, `parse_code_list` (reads units), `claim_changes(final, billed)`, `parse_note_filename`, `is_known_cpt` |
| `fees.py` | `fee_schedule_for(service_date)` (None for a year not vendored), `load_fee_schedule(year)`, `FeeSchedule.unit_amount / line / estimate`, `ClaimEstimate` (`total`, `unpriced`), `rate_setting_for(place_code)`, `FeeDataCorrupt` (CMS CY 2026 PFS RVU26D, checksummed manifest) |
| `places.py` | `setting_for(place_code)` |
| `npi.py` | `is_valid_npi` |
| `credentials.py` | `is_taxonomy_code` (NUCC: 10 characters ending in X), `is_valid_dea` (DEA shape and check digit), `LICENSE_STATES` (50 states, DC and five territories) |
| `mips_catalog.py`, `cms_mips_2026.py`, `mips_reporting_codes.py` | CMS MIPS 2026 catalog, standard measures, reporting codes (vendored from ChartMate) |
| `mips_scope.py` | `MipsScope`, `validate_measure_ids`, `practice_scope` |

## backend/app/ai

| Module | Provides |
|---|---|
| `contracts.py` | `ReviewInputs`, `ReviewReport` and its section models, `ReviewOutcome`, `ModelClient`, `ModelReply` |
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
| `object_store.py` | `ObjectStore` protocol (`put`, `get`, `signed_url`, `delete`, `delete_prefix` refusing anything that is not a folder), `S3ObjectStore` (S3 and R2; `client=` for a stubbed client), key builders `note_document_key`, `note_document_revision_key`, `analysis_response_key`, `practice_prefix` |
| `messenger.py` | `Messenger` protocol, `build_messenger` (email: SES, SMTP or outbox; texts: SNS, Twilio or outbox), `OutboxMessenger` |
| `email_senders.py`, `sms_senders.py` | `SesEmail`, `SmtpEmail`, `SnsSms`, `TwilioSms` |
| `mail_layout.py` | `html_from_text` (the HTML version of every email) |
| `pdf_text.py` | `read_pdf_text`, `DocumentUnreadable` |
| `gemini.py` | `GeminiClient` (the `ModelClient` for Gemini on the Developer API or Vertex AI, `GEMINI_BACKEND`), `VERTEX_PDF_TOO_LARGE` |
| `google_oidc.py` | `GoogleSignIn` protocol, `GoogleOidc`, `build_google_sign_in`, `GoogleIdentity`, `GoogleRefused`, `GoogleUnreachable`, `pkce_challenge` |

## backend/app/services (shared by several routes)

| Module | Provides |
|---|---|
| `finding.py` | `Finding`, `CODE_CHANGE_ACTIONS`, `SEVERE_AUDIT` (also importable from `findings.py`) |
| `findings.py` | `build_findings`, `visit_findings` |
| `code_additions.py` | `modifier_findings`, `add_on_findings`, `visit_code` |
| `risk_adjustment.py` | `risk_adjustment_findings(report, billed, icd, model)` |
| `routing.py` | `place(..., billed_diagnoses=)`, `has_diagnosis_codes`, `claim` (keeps units), `choices_for`, `open_questions` |
| `estimates.py` | `claim_estimate(codes, place_code, service_date)`, `claim_amount`, `estimate_difference`, `note_estimate`, `money` (Medicare national estimates) |
| `placement.py` | `current_findings`, `current_decisions`, `refresh_placement` |
| `analysis.py` | `request_analysis`, `claim_next`, `run_analysis`, `next_revision`, `latest_codes` |
| `audit_log.py` | `record_access`, `record_provider_access`, `record_activity`, `record_sign_in` |
| `auth.py` | `sign_in_user` (the one sign-in policy), `start_session`, `end_all_sessions`, `issue_user_token` |
| `rate_limits.py` | `RateRule`, `hit(db, rule, key)`, the rules (`LOGIN_PER_EMAIL` and the rest) |
| `two_step.py` | `enrol_secret`, `accept_code` (replay-safe, re-encrypts legacy secrets), `forget_two_step` |
| `recovery_codes.py` | `replace_recovery_codes`, `use_recovery_code`, `clear_recovery_codes`, `remaining_recovery_codes` |
| `password_reset.py` | `send_reset_email` (used by forgot password, Team and HQ) |
| `note_texts.py` | `note_texts(db, note_id)`, `current_texts(texts)` (from the latest `document` revision onward; used by the analysis and the note view) |
| `uploads.py` | `check_pdf(name, data)` (PDF signature and size), `create_upload`, `batch_history` |
| `records.py` | `replace_document`, `NewDocument`, `access_log_page`, `retention_cutoff(now, zone, years)`, `purge_access_logs(db, now) -> int`, `delete_practice` |
| `provider_details.py` | `validated_details`, `details_view`, `DETAIL_FIELDS` (provider credentialing) |
| `payers.py` | `payer_list`, `has_active_payer`, `add_payer`, `change_payer`, `remove_payer`, `PLAN_TYPES` |
| `worklists.py` | `queue_query(..., assigned=)` (`UNASSIGNED` for none), `queue_rows`, `lane_counts(db, practice_id, now=)`, `summary`, `user_names`, `assignee_name`, `QUEUE_STATUSES`, `DUE_SOON` |
| `assignment.py` | `assign_notes(db, actor, note_ids, user_id)` (the assignment rules; records `assigned`) |
| `digests.py` | `send_due_digests(db, messenger, now)`, `digest_text`, `set_digest_preference` |
| `search.py` | `search_notes(db, actor, text)`, `code_forms(term)` |
| `addenda.py` | `create_request`, `send_link`, `send_code`, `verify_code`, `provider_request`, `other_requests`, `switch_request`, `answer`, `addendum_text` |

## frontend/src (shared)

| Module | Provides |
|---|---|
| `components/shared/shortcuts/registry.ts` | `SHORTCUTS` (the one list of keyboard shortcuts, by scope `global`, `queue`, `review`), `comboFor`, `shortcutsIn(scope, role)`, `scopeForPath`, `isTyping`, `comboKeys` |
| `components/shared/shortcuts/useShortcuts.ts` | `useShortcuts(scope, handlers)` (ignores plain keys while typing and while a dialog is open) |
| `components/shared/shortcuts/ShortcutList.tsx`, `ShortcutsDialog.tsx` | the shortcut list (help page and the `?` dialog) |
| `components/shared/overlays.ts` | `openOverlay("search" \| "shortcuts")`, `closeOverlay`, `useOpenOverlay` |
| `components/shared/noteStatus.ts` | `noteStatus`, `DELETABLE_STATUSES`, `ASSIGNABLE_STATUSES` |
| `hooks/useAssignees.ts` | `useAssignees(user)` (who the user may assign notes to) |
| `components/ui/Pager.tsx` | `Pager` (offset pages with a total; text from `SHARED_TEXT.pager`), `offsetFrom(param)` |
| `components/shared/batchProgress.ts` | `batchCounts(batch)` (total, finished, pending, failed from counts by status) |
