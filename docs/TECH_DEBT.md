# Technical debt

Each entry: what is below standard, why it was left, what would clear it. The hygiene check
fails if the number of entries rises.

### API responses are untyped dictionaries

Request bodies are pydantic models, responses are dictionaries built by the services, so the
OpenAPI document does not describe them and the frontend mirrors them by hand. Clear it with
response models per route and generated frontend types.

### No rate limits

Login, the provider code endpoints and demo requests have no rate limit beyond the code attempt
cap. Clear it with a sliding-window limit per address and account.

### Nursing-facility initial visit once per stay

ChartMate's rule that 99304 to 99306 bill once per stay (CODE-100) is not ported because Bodha
has no stay history. Clear it once admission data is available.

### MIPS reporting codes not confirmed by a coder

The reporting-code table is vendored from ChartMate, where no coder has confirmed it yet
(CODE-18). Clear it with a coder's review.

### Uploaded PDFs can outlive a failed upload transaction

Files are validated before storage, but a database failure after storage leaves objects with no
note. Clear it with a sweep of unreferenced keys.

### ESLint plugins declare an older ESLint peer

`eslint-plugin-react`, `-import` and `-jsx-a11y` (through `eslint-config-next`) still declare
ESLint 9 as their peer, so ESLint 10 installs with peer overrides. Lint runs and reports correctly.
Clear it when the plugins declare ESLint 10.
