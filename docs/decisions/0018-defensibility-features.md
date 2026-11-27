# 0018 Defensibility: audit defense packet, same-provider day checks and the E/M level mix

Context: Bodha Coder's promise is that a practice bills the level it can defend. A practice facing a
payer or RAC audit needs the documentation, the reasoning and the decisions for one claim in one
file; compliance needs to see days that no single note review reveals (impossible time, cloned notes,
a run of top-level visits); and leadership needs each provider's level distribution against national
data, in both directions.

## Audit defense packet

- One PDF per note, built on request and never stored, so it always reflects the current records.
  The download is an export of PHI and is written to `access_log` as `downloaded defense packet`.
- Rendering goes through `adapters/pdf_writer.py` (reportlab 5.1.2, pure Python, BSD). The service
  builds neutral blocks (heading, text, facts, table, page break); the adapter is the only module that
  imports reportlab. fpdf2 was the alternative; reportlab's flowing layout (tables that split across
  pages, headings kept with what follows) needed less code.
- The font is Helvetica, a standard PDF font, so no font file is embedded or packaged. The Apple
  system font cannot be embedded. Characters outside its encoding (≥, ≤, →, ✓) are drawn from the
  standard Symbol and ZapfDingbats fonts by reportlab, so evidence quotes stay verbatim.
- The cover shows the patient's initials only and the page footer names only the practice; the full
  name, age and sex are on page 2. The file name carries the date of service and the first eight
  characters of the note id, never a name.
- The claim is the latest final code set once the note is approved; before that it is the derived
  claim, titled "Claim as decided, not approved". Units show for CPT lines only. The Medicare national
  estimate from `services.estimates` is shown per line when the fee schedule covers the year.
- Suggestions listed are those of the change kinds (visit level, diagnosis, procedure code, modifier)
  whose latest choice is accept, keep or add, excluding the risk-adjustment summary, which appears as
  a code-set check instead. A choice made by nobody is shown as "by default".
- Every answered request shows its questions and answers, then the signed addendum under the label
  "Addendum (amendment to the original note)" with its signing time and the provider, because CMS
  requires an amendment to be identified as one and dated (Medicare Program Integrity Manual,
  chapter 3, 3.3.2.5).
- The decision history is the decisions, every code-set revision and the note's decision actions in
  `access_log` (approved, asked provider, flagged, returned, reopened, signed addendum and the like);
  reads are left out.

## Same-provider day checks

- A provider-day is one provider and one date of service in one practice. Minutes come from the
  current analysis only (`report.em.time_minutes`), so a re-read never counts twice.
- The visit level of a note is its final code set once approved and its latest billed set otherwise
  (`services.visit_levels`, shared with the level mix). The share of the two highest levels counts
  only families with three or more levels; critical care and discharge codes are not levels.
- Near-duplicates compare the latest `document` text, ignoring blank lines, dropping the first and
  last three lines (headers, signatures), collapsing whitespace and case. Shingles are 5-character
  windows; a pair is cloned at Jaccard similarity 0.85 or more. A note with nothing left after
  trimming is not compared, and `compared` says how many were.
- Flags: more than 16 hours documented ("time over a plausible day"), any cloned pair, and a top-two
  share over 60% when the day has at least five leveled visits. The compliance list covers at most 92
  days (default 30) and lists only flagged days.

## E/M level mix against CMS specialty data

- Source: CMS *Evaluation and Management (E/M) Codes by Specialty*, CY 2025 (the latest published,
  page modified 2026-08-28), retrieved 2026-11-27. `tools/vendor_em_specialty.py` reduces the
  workbook to allowed services per specialty and code for the office new and established, nursing
  facility initial and subsequent, home new and established, and hospital inpatient or observation
  initial and subsequent families, and writes a gzip TSV with a manifest of source URL, year, dates,
  sizes and SHA-256 values. The loader checks the checksum, columns, family levels, row count and
  specialty count. Shares are derived from the stored services in one place, the loader. CMS leaves
  out rows under 11 allowed services, so a missing level reads as a share of 0; one row without a
  specialty is dropped and counted in the manifest. The file carries the AMA notice on CPT codes; only
  code numbers and counts are vendored.
- A provider's specialty text maps to a CMS specialty by exact name (case and spacing ignored, `&` read
  as "and") or a short alias list (family medicine, pediatrics, OB/GYN and others). Anything else has
  no benchmark and the screen says so; there is no default specialty.
- A level is an outlier when its share differs from the CMS share by more than 15 points, with at
  least 10 visits in the family so a handful of visits is never called an outlier. A family is also an
  outlier when a chi-square goodness-of-fit test against the CMS shares gives p < 0.01 with at least
  30 visits. Levels are pooled in order until each pooled expected count is at least 5 (Cochran's
  rule); a remainder joins the last pooled cell; fewer than two cells is no test. The upper tail uses
  the closed forms of the regularised incomplete gamma function for whole degrees of freedom
  (Abramowitz and Stegun 26.4.4 and 26.4.5), checked against the published 1% critical values.
- Both directions count: the lean is "higher" or "lower" by the mean level index against the CMS
  mean, so under-coding shows as clearly as over-coding.

## Follows

- Nothing is stored and no migration is needed; every check reads existing tables.
- The next CMS file (CY 2026) is vendored by running the tool with its URL and dates and adding the
  year; `BENCHMARK_YEAR` names the one in use.
- `services.insights` keeps its own private batched latest-code-set query; `services.visit_levels`
  has a second one. They should become one shared function.
