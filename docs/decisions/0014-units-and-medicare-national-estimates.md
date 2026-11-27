# 0014 Units on the claim and Medicare national estimates

Context: add-ons billed more than once (96127 per instrument, 99417 and G2212 per 15 minutes, 99292
per 30 minutes) were added once and the coder set the units (0010). Coders and admins also asked
what a change is worth.

## Units

- `Code` has `units` (1 to 99, default 1; a diagnosis has 1). Code lists read `96127x2`,
  `96127 x 2` and `96127×2`, with modifiers before the units (`97597-59x3`); `99214-X2` stays the
  patient-relationship modifier X2, and the placeholder X of ICD-10-CM codes (`O40.1XX0`) is never
  read as units. The label is `96127 ×2`; the typed form, used by the CSV `cpt` column, is
  `96127x2`.
- Code sets are JSON lists, so units are one more key (`"units"`). A stored row without it reads as
  one unit; no migration.
- The E/M answer gives each add-on `units`, counted as the prompt's STEP 4 says. Units outside 1 to
  99 make the add-on a `review` suggestion. The suggestion keeps them in `detail.units`; the claim
  adds the code with them and keeps billed units through replacements and modifiers.
- `claim_changes` counts a line whose modifiers or units changed as one change.
- Prompt version 2026.11.3.

## Medicare national estimates

- Source: the CMS CY 2026 PFS Relative Value File, release RVU26D (October 2026, released
  2026-08-26), the nonQPP PPRRVU file, rows with a blank modifier: status, work, non-facility and
  facility practice expense and malpractice RVUs. Vendored as `codes/data/pfs_rvu_2026.tsv.gz` with
  a manifest holding the source URL, retrieval date and SHA-256 values; `codes/fees.py` refuses a
  file whose checksum or counts differ.
- Amount per unit = (work + practice expense + malpractice RVU) × the conversion factor, rounded
  half up to the cent; a line is that times its units. No GPCI, so it is the national amount, not a
  locality's and never the practice's payment. Every screen labels it "Estimated Medicare national".
- Conversion factor 33.4009, the CY 2026 factor for clinicians who are not Qualifying APM
  Participants (the nonQPP file); a practice reporting MIPS is in that group. The QP factor
  (33.5675) is recorded in the manifest.
- Only status A, R and T with RVUs above zero have an amount (the README: only those RVUs are used
  for Medicare payment). Every other status, a code not in the file, and a line with a modifier that
  changes the payment (26, TC, 53, 50, 51, 62, 66, 80, 81, 82, AS) shows "—". Multiple-procedure,
  bilateral and other payment adjustments are not applied.
- Facility or non-facility rate from the place of service, as listed in the Medicare Claims
  Processing Manual, chapter 12, section 20.4.2: 02, 19, 21, 22, 23, 24, 26, 31, 34, 41, 42, 51, 52,
  53, 56, 61 are facility; the listed non-facility codes (11, 12, 13, 10, 32 and the rest) are
  non-facility. POS 02 (telehealth outside the home) pays the facility rate and POS 10 (in the
  home) the non-facility rate, so 02 is facility here. A place in neither list has no estimate.
- One release per calendar year: the latest quarterly release prices every 2026 date of service;
  other years have no estimate until their file is vendored.
- The schedule is loaded once per process (`functools.cache` in `codes/fees.py`): it is read-only
  vendored data, and note review, billing rows and insights all read it without the API wiring a
  dependency through every route.

## Coder productivity

Insights lists, per person who approved notes in the period: approvals, the median minutes from
the current analysis finishing (the note became ready) to approval, and how many approved claims
differ from the billed codes. A note whose approval precedes its current analysis is left out of
the median.
