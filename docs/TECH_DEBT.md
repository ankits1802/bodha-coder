# Technical debt

Each entry: what is below standard, why it was left, what would clear it. The hygiene check
fails if the number of entries rises.

### API responses are untyped dictionaries

Request bodies are pydantic models, responses are dictionaries built by the services, so the
OpenAPI document does not describe them and the frontend mirrors them by hand. Clear it with
response models per route and generated frontend types.

### Nursing-facility initial visit once per stay

ChartMate's rule that 99304 to 99306 bill once per stay (CODE-100) is not ported because Bodha
has no stay history. Clear it once admission data is available.

### MIPS reporting codes not confirmed by a coder

The reporting-code table is vendored from ChartMate, where no coder has confirmed it yet
(CODE-18). Clear it with a coder's review.

### Stored files can outlive their notes

Files are validated before storage, but a database failure after storage leaves objects with no
note, and when deleting a note's or a deleted practice's files fails after its records are gone the
failure is only logged. Deleting a note removes its current PDF and analysis replies but not the
earlier PDFs a replacement kept. Clear it with a sweep of unreferenced keys and by deleting a note's
whole folder (`ObjectStore.delete_prefix`).

### ESLint plugins declare an older ESLint peer

`eslint-plugin-react`, `-import` and `-jsx-a11y` (through `eslint-config-next`) still declare
ESLint 9 as their peer, so ESLint 10 installs with peer overrides. Lint runs and reports correctly.
Clear it when the plugins declare ESLint 10.

### Audit samples are grouped through JSON

Blind-audit samples are tied together by an id stored in `audit_samples.result`, not by a samples table, so
listing samples scans that JSON. Clear it with an `audit_runs` table that audit samples reference.

### ICD-10 agreement intervals pool codes

The Wilson intervals for ICD-10 precision and recall treat every code as independent, which understates the
uncertainty when one note contributes many codes. Clear it with a per-note bootstrap.

### Remittance appeal dates do not follow setting changes

Changing a practice's appeal window does not recompute appeal-by dates already stored on remittance lines.
Clear it by computing the date when the line is read.

### Email intake needs a small Lambda

Practices that send notes by email need an SES receipt rule and a small function that saves attachments into
their inbox folder; the repository documents it in `docs/DEPLOY-INTAKE.md` but does not include the function.
Clear it by adding the function and its deployment.

### Diagnosis pointers are positional

Claim lines point to the first four diagnoses because Bodha does not record which diagnosis supports which
procedure. Clear it by letting the coder link diagnoses to lines in note review.

### Python dependencies are pinned only at the top level

`pyproject.toml` pins direct dependencies, but their own dependencies float, so two image builds can differ.
Clear it with a lock or constraints file generated on Linux and used by CI and the Docker build.

### Blind audits are blind only on the audit screens

A reviewer who can read notes can still open the same note in the queue and see Bodha's suggestions and the
coder's decisions. Clear it by hiding a sampled note's review from its assigned reviewer until they submit.

### Latest code sets are queried in more than one place

`services/code_sets.py` holds the single-note queries, but `insights` and `visit_levels` each keep a batched
"latest code set per note" query. Clear it by moving the batched form into `code_sets.py`.

### New ICD-10 codes have no HCC until the midyear mapping is vendored

The CMS-HCC V28 payment year 2027 initial mapping covers codes valid through FY2026, and age edits use the
age in the note rather than the age on 1 February of the payment year. Clear it by vendoring the midyear
files and taking the date of birth into account when it is known.

### Intake is attributed to the first admin

Notes ingested from a watched folder are recorded as uploaded by the practice's first active admin, and a
dropped file keeps its original name in storage until the next poll. Clear it with a system uploader and an
upload rule that renames files on arrival.

### Remittance duplicates are found by name

A remittance file is recognised as a repeat only when its name and bytes match an earlier upload. Clear it by
keying duplicates on the file's checksum alone.

### The note review top bar spells out its shortcuts

"Previous note (K)" and "Next note (J)" are written in `ReviewTopBar.tsx` instead of coming from the shortcut
registry. Clear it by reading them from the registry like the overlay does.

### Evaluation replies are keyed outside the storage adapter

The object key for evaluation replies is built in `services/evaluation_runs.py` rather than with the other key
builders in `adapters/object_store.py`. Clear it by moving the builder there.

