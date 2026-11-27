# 0021 MIPS reporting codes verified against the CMS 2026 specifications

Context: `backend/app/codes/mips_reporting_codes.py` vendors the quality-data codes Bodha shows for
each MIPS measure (`MIPS_REPORTING_CODES`). A wrong code or role on that card leads a practice to
report the wrong thing, so every row was checked against the CMS files.

## Sources

- Verified 2026-11-27.
- MIPS CQM:
  [2026-MIPS-CQM-Specifications-and-Supporting-Documents.zip](https://qpp-cm-prod-content.s3.amazonaws.com/uploads/3565/2026-MIPS-CQM-Specifications-and-Supporting-Documents.zip),
  SHA-256 `4198f636ebe80760d8de6ee10f7f286726197f4fa01d5fb298589b5de72ce796`.
- Medicare Part B Claims:
  [2026-Part-B-Claims-Measure-Specifications-and-Supporting-Documents.zip](https://qpp-cm-prod-content.s3.amazonaws.com/uploads/3564/2026-Part-B-Claims-Measure-Specifications-and-Supporting-Documents.zip),
  SHA-256 `787f5c7a1333b3cae229c4b58dee373ebb21f843cbfb24e12370fc21cf232f10`.
- Both hashes match `SPEC_BUNDLES`. Every measure PDF used reads "Version 10.0, December 2025",
  matching `SPEC_VERSION`.
- The CQM zip was repackaged on 2026-04-23. Its version history lists a single change after the
  2025-12-22 posting, dated 2026-03-30. That change touched diagnosis and denominator coding (#113,
  #236, #502, #504, #505, #513), not reporting codes.

## Method

- The measure PDFs were read with pypdf (the backend's PDF library). For each row, the code, the
  role label in front of it (Performance Met, Performance Not Met, Denominator Exception) or the
  Denominator Exclusion section it sits in, and the descriptor were matched against the text. The
  match ignored case, spacing and punctuation.
- Every measure was checked against its MIPS CQM PDF, which is also the row's `source`. The five
  claims measures (001, 128, 134, 226, 236) were also checked against their Medicare Part B Claims
  PDF.
- For the multi-criteria measures 226, 431 and 493, each row had to sit inside its own
  `SUBMISSION CRITERIA n` section and no other.
- Each measure's Performance Met, Not Met, Exception and Exclusion codes were also compared with the
  Single Source code tables in both zips.
- Note text was checked where cheap:
  - inverse measure (001)
  - MVP only and not telehealth eligible (128)
  - a visit measure for any age, and G8427 when the patient takes no medications (130)
  - the criteria used for performance and for data completeness (226, 431)
  - both blood pressure codes must be met, and the frailty age bands (236)
  - vaccine ages, the weighted average and patient-reported vaccines (493)
  - the absence of nursing-facility visit codes 99304-99310, 99315 and 99316 from the denominators
    of 001, 048, 117, 226, 236 and 431

## Result

- 11 measures and 108 rows were checked. With the claims PDFs that makes 154 row-and-spec checks.
- Every code, role, criterion and descriptor agrees with the specifications, and no row was changed.
- Every note claim that was checked holds.
- No omissions. The Single Source lists G0162, G0299, G0300, G0493 and G0494 among the exclusion
  codes for 001, 117 and 236. These codes help define frailty, alongside DME and ICD-10 codes.
  They are not quality-data codes in their own right. The rows correctly carry the composite
  codes: G2090 and G2091; G2106 and G2107; G2115, G2116 and G2118.
- The same checks were run on `SPECIFIED_REPORTING_CODES` (047, 126, 155, 238 and 317, 26 rows).
  They also agree.

## Not verified

- The Single Source tables do not contain measure 128 (MVP reporting only), so 128 rests on its two
  PDFs alone.
- The claims Single Source lists only the denominator exclusion and exception codes, so numerator
  codes for claims measures rest on the claims PDFs.
- The 001 claims PDF's text ends the M1212 descriptor at "during the measurement" without the word
  "period". The CQM PDF has the full wording that the row uses.
- The check compares text with text. Whether a code fits a given patient is still the coder's
  judgement. A certified coder's sign-off on these cards is still recommended.
