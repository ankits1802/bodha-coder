# 0022 Typed API responses and generated frontend types

Context: request bodies were pydantic models, but every response was a dictionary built by a
service, so the OpenAPI document described no response and `frontend/src/lib/api/types.ts` mirrored
about 150 shapes by hand. The two sides could drift without any check noticing.

## Choice

- Every JSON route names a pydantic response model with `response_model=`, from
  `backend/app/api/responses/<area>.py` (193 models, 104 routes). Services keep returning
  dictionaries: switching them to models would have touched every service and its tests for no
  change in behaviour, and the route is where the HTTP contract belongs.
- The JSON stays byte-for-byte the same shape:
  - `View` forbids undeclared keys, so a key the service builds and the model lacks fails the
    request and the test that reaches it, instead of disappearing.
  - `ExactRoute`, the `route_class` of every router, serialises with `exclude_unset`, so a response
    carries exactly the keys the service built: a key that is sometimes absent (`recovery_codes`,
    a payer flag's `earlier`, a stored code's `units` and `pointers`, a queued evaluation's empty
    summary) stays absent rather than becoming `null`.
  - Such keys are declared `Omittable[T] = None`: optional in the schema, never `null`, so the
    generated type is `key?: T`.
  - Fields that hold numbers mirror what the service builds (`float` for money and ratios,
    `int | float` for the model's scores), dates stay the ISO strings the services format, and a
    closed set is a `Literal` derived from the constant that defines it (`NOTE_STATUSES`, `LANES`,
    `PLAN_TYPES`, `PLANS`), not a copy.
- File downloads (claims CSV, defense packet PDF, addendum text) keep returning `Response`; they
  declare their media type with `file_download`. `POST /api/billing/claim-lines` declares its JSON
  model and its CSV alternative. The Google redirects declare `RedirectResponse`.
- `tools/export_openapi.py` writes `frontend/openapi.json` (sorted keys, two-space indent, LF) from
  `app.main.app.openapi()` with the placeholder `SECRET_KEY` and `S3_BUCKET` of the CI image smoke
  test, so it needs no database and no secret. The output does not depend on the working directory
  or a local `.env`.
- `npm run api:types` runs openapi-typescript 7.13.0 (npm `latest` on 2026-11-27) through its Node
  API with `defaultNonNullable: false` (a defaulted request field stays optional), then reprints the
  result with the TypeScript printer and `removeComments`, so `schema.ts` has no header and no JSDoc
  and passes the hygiene check and ESLint without exclusions.
- `types.ts` names the generated schemas for the screens (`NoteDetail = components["schemas"]["NoteDetail"]`)
  and derives literal unions from them (`NoteStatus = NoteSummary["status"]`). Kept hand-written:
  query and form types the client composes (`QueueQuery`, `UploadPlan`, `InviteBody`,
  `MemberUpdate`, `NewPractice`, `PracticeUpdate`, `HqActivityQuery`, `BillingShow`, `InsightDays`,
  `RemittanceFilter`), whose client types are narrower than the backend's loose `str` fields, and
  `MdmElements`, the reading of a finding's free-form `detail`.
- CI fails when either file differs from what the code produces: the backend job regenerates
  `openapi.json`, the frontend job regenerates `schema.ts` from it.

## Alternatives

- `@hey-api/openapi-ts` and Orval generate API clients as well as types; the project has one
  hand-written client (`lib/api/client.ts`) and needs types only.
- A generator written for this repository would avoid a dependency, but would need its own tests
  and upkeep for every JSON Schema form pydantic emits; openapi-typescript is the most used
  types-only generator and already handles discriminated unions, `additionalProperties: false` and
  nullable unions.
- openapi-typescript declares `typescript ^5.x` as its peer, and the project stays on TypeScript 6
  ([0007](0007-frontend-toolchain.md)). An npm `overrides` entry gives it the project's TypeScript;
  it uses only the printer and node factory API, which TypeScript 6 keeps. Recorded in the debt
  register until it declares TypeScript 6.

## Follows

- After changing a route, a response model or a request body, run `tools/export_openapi.py` and
  `npm run api:types` and commit both files.
- The JSON the API returns is unchanged. Corrections the generated types brought to the screens
  and their test fixtures: `NoteSummary` carries `payer`, `Checks` always carries `hcc`, `EmAction` includes
  `review` (a visit Bodha could not level), a sample's period may be `null` (shown as `—`), and an
  analysis's MIPS scope has a type instead of `unknown`.
- Error bodies (`{"error", "message"}`) are not described per route; the OpenAPI document still shows
  FastAPI's default 422 schema for them.
