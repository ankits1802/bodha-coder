# Decision log

One short record per decision, numbered in order. Records are history: a later choice is a new record,
and the earlier one is left as it was decided (some carry a short "Amended" note). The status says
whether a record still holds as written: `current`, or `amended by` the records that changed part of
it. No record has been replaced as a whole, so none is `superseded`. Records 0001 to 0024 carry no date
line; their date is the commit that added them.

| No. | Decision | Date | Status |
|---|---|---|---|
| [0001](0001-stack-and-legacy.md) | Stack and the legacy application | 2026-11-26 | current |
| [0002](0002-reuse-chartmate.md) | Reuse ChartMate's code sets and review flows | 2026-11-26 | current |
| [0003](0003-revisions-and-storage.md) | Every result and decision is a stored revision | 2026-11-26 | current |
| [0004](0004-routing.md) | Lanes | 2026-11-26 | amended by [0043](0043-one-findings-list-and-returns.md) |
| [0005](0005-provider-addenda.md) | Provider questions | 2026-11-26 | current |
| [0006](0006-frozen-initial-migration.md) | The first migration runs frozen SQL | 2026-11-26 | current |
| [0007](0007-frontend-toolchain.md) | Frontend toolchain versions | 2026-11-26 | current |
| [0008](0008-google-sign-in-and-recovery-codes.md) | Google sign-in, recovery codes and account security | 2026-11-26 | amended by [0026](0026-self-serve-sign-up.md), [0028](0028-subscription-billing.md) |
| [0009](0009-email-and-texts-through-aws.md) | Email through SES, texts through SNS or Twilio | 2026-11-26 | amended by [0030](0030-texts-only-when-set-up.md) |
| [0010](0010-modifiers-add-ons-and-hcc.md) | Modifiers, add-on codes, CPT-only claims, critical care and risk adjustment | 2026-11-26 | amended by [0014](0014-units-and-medicare-national-estimates.md), [0054](0054-prolonged-service-99417.md) |
| [0011](0011-practice-deletion-and-retention.md) | Replaced PDFs, access-log retention and deleting a practice | 2026-11-27 | amended by [0038](0038-seven-year-retention-and-tamper-evidence.md) |
| [0012](0012-vertex-ai.md) | Gemini on Vertex AI for PHI | 2026-11-27 | current |
| [0013](0013-postgres-job-queue-no-sqs.md) | The job queue stays in Postgres; no SQS | 2026-11-27 | current |
| [0014](0014-units-and-medicare-national-estimates.md) | Units on the claim and Medicare national estimates | 2026-11-27 | amended by [0054](0054-prolonged-service-99417.md) |
| [0015](0015-assignment-digests-and-provider-switch.md) | Who may assign notes, when the daily summary goes out, and how a provider moves between requests | 2026-11-27 | current |
| [0016](0016-containers-and-deployment.md) | Containers, logs and the AWS reference deployment | 2026-11-27 | current |
| [0017](0017-remittance-intake-query-governance.md) | Remittance loop, automatic intake and query governance | 2026-11-27 | amended by [0038](0038-seven-year-retention-and-tamper-evidence.md), [0046](0046-email-intake.md) |
| [0018](0018-defensibility-features.md) | Defensibility: audit defense packet, same-provider day checks and the E/M level mix | 2026-11-27 | amended by [0036](0036-review-audit-trail.md) |
| [0019](0019-ncci-edits-and-payer-rules.md) | NCCI edits, payer rules and claim lines | 2026-11-27 | amended by [0036](0036-review-audit-trail.md), [0052](0052-ncci-bypass-by-relationship.md) |
| [0020](0020-measured-accuracy-and-earned-autonomy.md) | Measured accuracy and earned autonomy | 2026-11-27 | amended by [0049](0049-synthetic-gold-set.md), [0053](0053-blind-audits-read-the-claim-as-uploaded.md), [0055](0055-evaluations-score-claim-lines.md) |
| [0021](0021-mips-codes-verified.md) | MIPS reporting codes verified against the CMS 2026 specifications | 2026-11-27 | current |
| [0022](0022-typed-responses.md) | Typed API responses and generated frontend types | 2026-11-27 | current |
| [0023](0023-demo-model-backend.md) | Demo model backend | 2026-11-27 | current |
| [0024](0024-ergonomics-pass.md) | Fewer steps and less waiting for the people who work notes all day | 2026-11-27 | amended by [0041](0041-streamlined-navigation-and-first-day.md) |
| [0025](0025-staging-on-aws.md) | Staging on AWS with OpenTofu | 2026-11-27 | amended by [0048](0048-vercel-retired.md) |
| [0026](0026-self-serve-sign-up.md) | Self-serve sign-up and more sign-in services | 2026-11-27 | amended by [0033](0033-hq-on-its-own-host.md), [0037](0037-multi-practice-membership.md), [0044](0044-organizations-and-domain-join.md), [0048](0048-vercel-retired.md) |
| [0027](0027-own-select-and-date-picker.md) | Our own select and date picker | 2026-11-27 | current |
| [0028](0028-subscription-billing.md) | Subscription billing with Stripe and PayPal | 2026-11-27 | amended by [0037](0037-multi-practice-membership.md), [0041](0041-streamlined-navigation-and-first-day.md), [0044](0044-organizations-and-domain-join.md), [0057](0057-organization-admins-keep-billing-access.md) |
| [0029](0029-nonce-content-security-policy.md) | A nonce for every page's scripts | 2026-11-27 | current |
| [0030](0030-texts-only-when-set-up.md) | Texts only when they can be sent | 2026-11-27 | current |
| [0031](0031-pricing-rendered-on-the-server.md) | Pricing rendered on the server | 2026-11-27 | current |
| [0032](0032-product-name.md) | Product name: Bodha Assure | 2026-11-28 | current |
| [0033](0033-hq-on-its-own-host.md) | HQ on its own host, with its own accounts | 2026-11-28 | amended by [0063](0063-longer-sign-in.md) |
| [0034](0034-sample-review-and-pricing-teaser.md) | Sample review and pricing teaser on the landing page | 2026-11-28 | current |
| [0035](0035-model-spend-per-provider.md) | Model spend per practice and per provider | 2026-11-28 | amended by [0042](0042-inbox-upload-matching-queue-views-hq-page.md) |
| [0036](0036-review-audit-trail.md) | Review audit trail | 2026-11-28 | amended by [0038](0038-seven-year-retention-and-tamper-evidence.md) |
| [0037](0037-multi-practice-membership.md) | One person, several practices | 2026-11-28 | amended by [0038](0038-seven-year-retention-and-tamper-evidence.md) |
| [0038](0038-seven-year-retention-and-tamper-evidence.md) | Seven-year retention and tamper evidence | 2026-11-28 | amended by [0046](0046-email-intake.md) |
| [0039](0039-first-sign-in-tour.md) | A tour on first sign-in | 2026-11-28 | amended by [0041](0041-streamlined-navigation-and-first-day.md) |
| [0040](0040-e-signatures-and-sealed-records.md) | Electronic signatures and sealed records | 2026-11-28 | current |
| [0041](0041-streamlined-navigation-and-first-day.md) | Fewer sidebar entries and a guided first day | 2026-11-28 | amended by [0064](0064-everyone-uploads.md) |
| [0042](0042-inbox-upload-matching-queue-views-hq-page.md) | Inbox, upload matching, queue views and the HQ practice page | 2026-11-28 | amended by [0043](0043-one-findings-list-and-returns.md) |
| [0043](0043-one-findings-list-and-returns.md) | One findings list, and returns to the coder that keep their reason | 2026-11-28 | current |
| [0044](0044-organizations-and-domain-join.md) | Organizations, combined billing and joining by email domain | 2026-11-28 | amended by [0057](0057-organization-admins-keep-billing-access.md) |
| [0045](0045-practice-measures-and-usage-timing.md) | Practice-defined quality measures and privacy-safe usage timing | 2026-11-28 | current |
| [0046](0046-email-intake.md) | Email intake: an address per practice, checked by the worker | 2026-11-28 | current |
| [0047](0047-error-tracking-off-until-configured.md) | Error tracking with Sentry, off until configured | 2026-11-28 | current |
| [0048](0048-vercel-retired.md) | Vercel retired | 2026-11-28 | current |
| [0049](0049-synthetic-gold-set.md) | A synthetic gold set for measured accuracy | 2026-11-28 | amended by [0052](0052-ncci-bypass-by-relationship.md), [0054](0054-prolonged-service-99417.md), [0055](0055-evaluations-score-claim-lines.md), [0059](0059-payer-known-when-the-note-is-read.md) |
| [0050](0050-browser-journeys-and-production-canary.md) | Browser journeys in CI and a nightly production canary | 2026-11-28 | current |
| [0051](0051-clearinghouse-837p.md) | Claims to a clearinghouse as X12 837P, beside the claim lines CSV | 2026-11-28 | current |
| [0052](0052-ncci-bypass-by-relationship.md) | NCCI pair edits are bypassed by the modifier that fits the pair | 2026-11-28 | current |
| [0053](0053-blind-audits-read-the-claim-as-uploaded.md) | Blind audits freeze Bodha's suggestion from the claim as uploaded | 2026-11-28 | current |
| [0054](0054-prolonged-service-99417.md) | CPT 99417 for prolonged office time, beside Medicare's G2212 | 2026-11-28 | amended by [0059](0059-payer-known-when-the-note-is-read.md) |
| [0055](0055-evaluations-score-claim-lines.md) | Evaluation runs score procedure lines, add-ons, units and place of service | 2026-11-28 | current |
| [0056](0056-hq-plan-on-renewal-and-status-follows-plan.md) | HQ sets the plan with the renewal, and a practice's status follows its plan | 2026-11-28 | current |
| [0057](0057-organization-admins-keep-billing-access.md) | Organization admins keep billing access after their organization's plan ends | 2026-11-28 | current |
| [0058](0058-figures-open-their-records.md) | A dashboard figure opens the records it counts | 2026-11-28 | current |
| [0059](0059-payer-known-when-the-note-is-read.md) | The payer is known when the note is read | 2026-11-28 | current |
| [0060](0060-ehr-connection-over-fhir.md) | EHR connection: signed visit notes pulled over FHIR | 2026-11-28 | current |
| [0061](0061-saml-single-sign-on.md) | SAML 2.0 single sign-on for practices and organizations | 2026-11-28 | current |
| [0062](0062-accessibility-sweep-of-every-screen.md) | A WCAG 2.2 AA sweep of every screen in CI | 2026-11-28 | current |
| [0063](0063-longer-sign-in.md) | People stay signed in for days, not minutes | 2026-11-28 | current |
| [0064](0064-everyone-uploads.md) | Everyone in a practice can upload, and the drop area is always in view | 2026-11-28 | current |
| [0065](0065-appearance.md) | Appearance: theme, text size and reduce motion for each person | 2026-11-28 | current |

A new record takes the next number, a `# NNNN Title` heading and a `Date:` line, and gets its row here.
When it changes an earlier record, say which one in the new record and update the earlier one's status
above.
