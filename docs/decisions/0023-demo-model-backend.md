# 0023 Demo model backend

Context: the Gemini account ran out of credits, so no note reached review on a development machine
and the review, query, compliance and billing screens could not be measured or demonstrated with
real flows.

## Choice

- `GEMINI_BACKEND=demo` builds `adapters.demo_model.DemoModelClient` in the worker instead of
  `GeminiClient`. It is a `ModelClient` like any other: `review_note`, the bundle validation, the
  findings and the routing run unchanged, so every lane is reached the way a real read reaches it.
- It reads the requested parts from the response schema and the billed codes and date of service
  from the encounter context in the prompt, and answers each part with a canned, schema-valid
  section. Quotes are copied from the note's numbered plan lines; patient facts from its header.
- The outcome is chosen from the first byte of the SHA-256 of the PDF (or of the document text when
  the text is sent) modulo five: matches, billed too high, billed too low, CDI query, audit risk.
  A note with a signed addendum reads as matching, so an answered query lets the note move on.
- Adapters do not import `codes`, so the worker hands it a `DemoCodeBook`: `codes.em.em_ladder`
  for the levels of a visit code's family, and `IcdCatalog.describe` for diagnosis names.
- `Settings.app_environment` (`APP_ENVIRONMENT`: `development`, `staging`, `production`) is new
  and defaults to `production`. A validator refuses `GEMINI_BACKEND=demo` in production, so the API
  and the worker fail at start-up rather than producing canned findings for real notes. The default
  fails closed: a deployment that never sets the variable cannot run the demo.

## Alternatives

- A fake reviewer (like the tests' `ScriptedReviewer`) in place of `review_note` would skip the
  prompt, bundle validation and top-up, so the demo would not exercise the real path.
- Recognising production from `APP_URL` (https, not loopback) would refuse a staging host on
  synthetic data behind TLS, and would accept a production host misconfigured with http.

## Follows

- Production task definitions carry `APP_ENVIRONMENT=production` explicitly
  ([DEPLOY.md](../DEPLOY.md)); `.env.example` carries `development`.
- `docs/OPERATIONS.md` describes the backend and its refusal.
