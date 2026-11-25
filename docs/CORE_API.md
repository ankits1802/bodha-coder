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
| `calendar.py` | `zone_named`, `day_bounds`, `today_in` (practice calendar days) |
| `deps.py` | `Db`, `Actor`, `current_actor`, `require(*roles)`, `ProviderActor`, `current_provider`, `ensure_practice_open`, `PlanEnded` |

## backend/app/codes

| Module | Provides |
|---|---|
| `icd.py` | `load_catalog()`, `IcdCatalog.for_service_date`, `IcdRelease.get / more_specific / is_unspecified`, `format_icd`, `fiscal_year_for` |
| `em.py` | `EM_FAMILIES` (each `EmFamily` with its levels and add-ons, such as 99292), `compare_em`, `describe_em`, `is_em_code` |
| `modifiers.py` | `VISIT_MODIFIERS`, `PROCEDURE_MODIFIERS`, `allowed_modifiers(code)`, `modifier_meaning(code, modifier)` |
| `hcc.py` | `load_hcc_model(payment_year)`, `hcc_model_for(payment_year)` (None when not vendored), `HccModel.hccs_for / payment_hccs / score / label / factor / is_trumped`, `HccPatient`, `payment_year_for(service_date)`, `segment_for(age)`, `sex_code`, `HccDataCorrupt` (CMS-HCC V28, checksummed manifest) |
| `billing_codes.py` | `Code`, `parse_code_list`, `parse_note_filename`, `is_known_cpt` |
| `places.py` | `setting_for(place_code)` |
| `npi.py` | `is_valid_npi` |
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
| `object_store.py` | `ObjectStore` protocol, `S3ObjectStore` (S3 and R2), key builders |
| `messenger.py` | `Messenger` protocol, `build_messenger` (email: SES, SMTP or outbox; texts: SNS, Twilio or outbox), `OutboxMessenger` |
| `email_senders.py`, `sms_senders.py` | `SesEmail`, `SmtpEmail`, `SnsSms`, `TwilioSms` |
| `mail_layout.py` | `html_from_text` (the HTML version of every email) |
| `pdf_text.py` | `read_pdf_text`, `DocumentUnreadable` |
| `gemini.py` | `GeminiClient` (the `ModelClient` for Gemini) |
| `google_oidc.py` | `GoogleSignIn` protocol, `GoogleOidc`, `build_google_sign_in`, `GoogleIdentity`, `GoogleRefused`, `GoogleUnreachable`, `pkce_challenge` |

## backend/app/services (shared by several routes)

| Module | Provides |
|---|---|
| `finding.py` | `Finding`, `CODE_CHANGE_ACTIONS`, `SEVERE_AUDIT` (also importable from `findings.py`) |
| `findings.py` | `build_findings`, `visit_findings` |
| `code_additions.py` | `modifier_findings`, `add_on_findings`, `visit_code` |
| `risk_adjustment.py` | `risk_adjustment_findings(report, billed, icd, model)` |
| `routing.py` | `place(..., billed_diagnoses=)`, `has_diagnosis_codes`, `claim`, `choices_for`, `open_questions` |
| `placement.py` | `current_findings`, `current_decisions`, `refresh_placement` |
| `analysis.py` | `request_analysis`, `claim_next`, `run_analysis`, `next_revision`, `latest_codes` |
| `audit_log.py` | `record_access`, `record_provider_access`, `record_activity`, `record_sign_in` |
| `auth.py` | `sign_in_user` (the one sign-in policy), `start_session`, `end_all_sessions`, `issue_user_token` |
| `rate_limits.py` | `RateRule`, `hit(db, rule, key)`, the rules (`LOGIN_PER_EMAIL` and the rest) |
| `two_step.py` | `enrol_secret`, `accept_code` (replay-safe, re-encrypts legacy secrets), `forget_two_step` |
| `recovery_codes.py` | `replace_recovery_codes`, `use_recovery_code`, `clear_recovery_codes`, `remaining_recovery_codes` |
| `password_reset.py` | `send_reset_email` (used by forgot password and by Team) |
