# 0002 Reuse ChartMate's code sets and review flows

Context: ChartMate already holds checked ICD-10-CM data, the CMS MIPS catalog and the CDI, audit,
E/M and MIPS prompts. Taken from the ChartMate commit `b9935cef`.

Choice: vendor, unchanged, `icd10cm_2026/2027.tsv.gz` with their manifests, `catalog_pfs.py`,
`cms_mips_2026.py` and `mips_catalog.py`; adapt only the imports of `mips_reporting_codes.py`
and the pure parts of `mips_scope.py` (scope source `practice`, no facility level); port the
prompts and schemas of `scan_cdi_gaps`, `generate_audit_checklist`, `suggest_cpt_em_codes` and
`identify_mips_quality_measures` behind Bodha's `ModelClient`, as one bundled call per note with
a top-up call for sections that fail validation.

Dropped: ChartMate's practice-specific plan wording, the "always true" audit lines, note-editing
remediation, the replay hooks, the split-into-separate-calls rescue on timeout, and the retry of
unrecognised errors (it hid bugs as outages).

Fixed while porting:

- new-patient office time bands, and the deleted code 99318
- prescription drug management is Moderate risk; two or more stable chronic illnesses are a
  Moderate problem; an acute illness with systemic symptoms is Moderate, not High
- stable COPD is J44.9, not J44.0
- audit standards judge what the note shows instead of always passing; a short review of systems
  or exam no longer fails a note
- CDI queries carry no pre-written answer text, so they cannot lead the provider

Follows: when ChartMate updates a vendored file, copy it again rather than editing Bodha's copy.
