# Shared components

Check here before writing a helper.

## backend/app/core

| Module | Provides |
|---|---|
| `config.py` | `Settings`, `get_settings()` |
| `db.py` | `engine`, `SessionFactory`, `get_session` |
| `security.py` | `hash_password`, `verify_password`, `issue_token`, `read_token`, `digest`, `same_digest`, `random_token`, `random_code`, TOTP helpers |
| `errors.py` | `AppError` and `Unauthorized`, `Forbidden`, `NotFound`, `Conflict`, `Invalid`, `Unavailable` |
| `roles.py` | role groups used by every route guard |
| `calendar.py` | `zone_named`, `day_bounds`, `today_in` (practice calendar days) |
| `deps.py` | `Db`, `Actor`, `current_actor`, `require(*roles)`, `ProviderActor`, `current_provider` |

## backend/app/codes

| Module | Provides |
|---|---|
| `icd.py` | `load_catalog()`, `IcdCatalog.for_service_date`, `IcdRelease.get / more_specific / is_unspecified`, `format_icd`, `fiscal_year_for` |
| `em.py` | `EM_FAMILIES`, `compare_em`, `describe_em`, `is_em_code` |
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
| `cdi.py`, `audit.py`, `mips.py` | CDI, audit checklist and MIPS section models (ChartMate field names) |
| `prompts/` | one module per section, plus the shared frame and context |

## backend/app/adapters

| Module | Provides |
|---|---|
| `object_store.py` | `ObjectStore` protocol, `S3ObjectStore` (S3 and R2), key builders |
| `messenger.py` | `Messenger` protocol, `SmtpTwilioMessenger` |
| `pdf_text.py` | `read_pdf_text`, `DocumentUnreadable` |
| `gemini.py` | `GeminiClient` (the `ModelClient` for Gemini) |

## backend/app/services (shared by several routes)

| Module | Provides |
|---|---|
| `findings.py` | `Finding`, `build_findings` |
| `routing.py` | `place`, `claim`, `choices_for`, `open_questions` |
| `placement.py` | `current_findings`, `current_decisions`, `refresh_placement` |
| `analysis.py` | `request_analysis`, `claim_next`, `run_analysis`, `next_revision`, `latest_codes` |
| `audit_log.py` | `record_access`, `record_provider_access`, `record_activity` |
