# Technical debt

Each entry: what is below standard, why it was left, what would clear it. The hygiene check
fails if the number of entries rises.

### Coder sign-off pending: MIPS reporting codes and the evaluation gold set

The MIPS reporting codes were verified against CMS 2026 specifications on 2026-11-27; a coder's
sign-off is still recommended ([0021](decisions/0021-mips-codes-verified.md)). The 48 expected claims of
the synthetic gold set (`tools/gold_set/cases.json`) were written by construction and pass the validator,
but no certified coder has audited them, so accuracy numbers from that set are provisional
([0049](decisions/0049-synthetic-gold-set.md)). The prolonged time rules (99417 only with 99205 or 99215,
although CPT and the NCCI add-on table also list 99245, 99345, 99350 and 99483; 99417 on a Medicare
Advantage claim as a risk) await the same review ([0052](decisions/0052-prolonged-service-99417.md)). Clear
each part when a certified coder has reviewed it and the review (who, when, changes made) is recorded in its
decision.

### ESLint plugins declare an older ESLint peer

`eslint-plugin-react`, `-import` and `-jsx-a11y` (through `eslint-config-next`) still declare
ESLint 9 as their peer, so `npm ls` reports ESLint 10 as an invalid peer of them. Lint runs and reports
correctly. Checked on 2026-11-27 against the npm `latest` tags: `eslint` 10.15.0, `eslint-config-next`
16.4.6 (peer `>=9.0.0`), `eslint-plugin-react-hooks` 7.1.1 (declares `^10.0.0`), `eslint-plugin-react`
7.37.5 (up to `^9.7`), `eslint-plugin-import` 2.32.0 (up to `^9`), `eslint-plugin-jsx-a11y` 6.10.2 (up to
`^9`). Clear it when those three declare ESLint 10.

### openapi-typescript declares a TypeScript 5 peer

`openapi-typescript` 7.13.0 (npm `latest` on 2026-11-27) declares `typescript ^5.x` as its peer, and
the project is on TypeScript 6.0.3, so `frontend/package.json` overrides that peer with the project's
TypeScript. The generator uses only the printer and node factory API, and CI fails if `schema.ts`
ever comes out different ([0022](decisions/0022-typed-responses.md)). Clear it by removing the
`overrides` entry once openapi-typescript declares TypeScript 6.

### New ICD-10 codes have no HCC until the midyear mapping is vendored

The CMS-HCC V28 payment year 2027 initial mapping covers codes valid through FY2026, so FY2027 codes map to
no HCC. On 2026-11-27 CMS had published no PY2027 midyear or final mapping. Clear it by vendoring that
mapping like the initial files (manifest and checksums) once CMS posts it, for the dates of service it covers.

